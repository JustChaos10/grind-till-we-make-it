export const fmt = (value: number | null | undefined, digits = 1) =>
  value == null || !Number.isFinite(value)
    ? '—'
    : value.toLocaleString(undefined, { maximumFractionDigits: digits })

export class ApiError extends Error {
  detail: unknown

  constructor(message: string, detail: unknown) {
    super(message)
    this.detail = detail
  }
}

export async function api<T>(path: string, options?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(path, {
      ...options,
      headers: { 'Content-Type': 'application/json', ...options?.headers },
    })
  } catch (error) {
    if (error instanceof Error && error.name === 'AbortError') throw error
    if (error instanceof TypeError) {
      throw new Error('Could not connect to the IndoFlow API. Check the connection and try again.')
    }
    throw error
  }
  if (!response.ok) {
    const apiUnavailable = [502, 503, 504].includes(response.status)
    let message = apiUnavailable
      ? 'The IndoFlow API is unavailable. Try again. If the problem continues, ask your administrator to check the API connection.'
      : `${response.status} ${response.statusText}`
    let detail: unknown
    try {
      const body = await response.json()
      detail = body.detail
      message = describeApiError(body.detail) || body.message || message
    } catch {
      /* keep the fallback message */
    }
    if (response.status === 401 || response.status === 403) {
      const reason = response.status === 401 ? 'Authentication required' : 'Access denied'
      throw new Error(`${reason}. Ask the administrator to check access through the API proxy.`)
    }
    throw new ApiError(message, detail)
  }
  let body: unknown
  try {
    body = await response.json()
  } catch (error) {
    if (error instanceof Error && error.name === 'AbortError') throw error
    throw invalidResponse(path)
  }
  const validate = responseValidators[path.split('?')[0]]
  if (validate && !validate(body)) throw invalidResponse(path)
  return body as T
}

function describeApiError(detail: unknown): string | null {
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    const messages = detail.map((entry) => {
      if (typeof entry === 'string') return entry
      if (!entry || typeof entry !== 'object') return String(entry)
      const item = entry as { loc?: unknown[]; msg?: unknown }
      const location = Array.isArray(item.loc) ? item.loc.map(String).join(' → ') : ''
      return [location, typeof item.msg === 'string' ? item.msg : 'Invalid value']
        .filter(Boolean)
        .join(': ')
    })
    return messages.join('; ')
  }
  if (detail && typeof detail === 'object') {
    const item = detail as { msg?: unknown; message?: unknown }
    return typeof item.msg === 'string'
      ? item.msg
      : typeof item.message === 'string'
        ? item.message
        : JSON.stringify(detail)
  }
  return null
}

// Validate data at the API boundary before it can replace a usable snapshot.
// Metrics may be absent or null: the UI explicitly renders those as unavailable.
type RecordValue = Record<string, unknown>
const record = (value: unknown): value is RecordValue =>
  value !== null && typeof value === 'object' && !Array.isArray(value)
const number = (value: unknown): value is number =>
  typeof value === 'number' && Number.isFinite(value)
const string = (value: unknown) => typeof value === 'string'
const optional = (test: (value: unknown) => boolean) => (value: unknown) =>
  value == null || test(value)
const fields = (value: unknown, names: string[], test: (value: unknown) => boolean) =>
  record(value) && names.every((name) => test(value[name]))
const list = (value: unknown, test: (item: unknown) => boolean) =>
  Array.isArray(value) && value.every(test)
const strings = (value: unknown) => list(value, string)
const metrics = (value: unknown) =>
  record(value) &&
  fields(
    value,
    [
      'late_orders',
      'avg_wip_age_hours',
      'throughput',
      'throughput_horizon_hours',
      'furnace_batch_efficiency_pct',
      'makespan_hours',
      'weighted_tardiness_hours',
    ],
    optional(number),
  ) &&
  fields(value, ['schedule_version_id', 'bottleneck_resource_id'], optional(string)) &&
  (value.resource_busy_hours == null ||
    (record(value.resource_busy_hours) && Object.values(value.resource_busy_hours).every(number)))
const delta = (value: unknown) =>
  record(value) &&
  fields(
    value,
    ['late_orders', 'avg_wip_age_hours', 'throughput', 'furnace_batch_efficiency_pct'],
    optional(number),
  ) &&
  fields(value, ['bottleneck_before', 'bottleneck_after'], optional(string))
const operation = (value: unknown) =>
  record(value) &&
  fields(
    value,
    ['work_order_id', 'wo_number', 'sku_code', 'resource_id', 'resource_name', 'plant', 'stage'],
    string,
  ) &&
  fields(value, ['start_hour', 'end_hour'], number) &&
  number(value.start_hour) &&
  number(value.end_hour) &&
  value.end_hour >= value.start_hour &&
  fields(value, ['batch_id', 'delay_reason'], optional(string)) &&
  typeof value.is_late === 'boolean'
const lateOrder = (value: unknown) =>
  record(value) &&
  fields(value, ['work_order_id', 'wo_number', 'explanation'], string) &&
  fields(value, ['due_date_hours', 'completion_hours', 'delay_hours', 'priority'], number)
const paired = (value: unknown, test: (item: unknown) => boolean) =>
  record(value) && list(value.baseline, test) && list(value.optimized, test)
const impact = (value: unknown) =>
  record(value) &&
  fields(value, ['work_order_id', 'wo_number'], string) &&
  fields(
    value,
    [
      'due_date_before_hours',
      'due_date_scenario_hours',
      'completion_before_hours',
      'completion_scenario_hours',
      'completion_delta_hours',
      'delay_delta_hours',
    ],
    number,
  ) &&
  typeof value.late_before === 'boolean' &&
  typeof value.late_scenario === 'boolean'

const responseValidators: Record<string, (value: unknown) => boolean> = {
  '/api/flow-board': (value) =>
    record(value) &&
    number(value.total_wip_orders) &&
    optional(number)(value.avg_wip_age_hours) &&
    list(
      value.queues,
      (queue) =>
        record(queue) &&
        string(queue.stage) &&
        number(queue.queue_depth) &&
        optional(number)(queue.avg_wip_age_hours),
    ) &&
    strings(value.active_bottleneck_alerts),
  '/api/catalog': (value) =>
    record(value) &&
    list(value.resources, (resource) =>
      fields(resource, ['id', 'name', 'plant', 'stage', 'status'], string),
    ) &&
    list(
      value.work_orders,
      (order) =>
        fields(order, ['id', 'wo_number', 'sku_code', 'stage', 'status'], string) &&
        fields(order, ['due_date_hours', 'priority'], number),
    ),
  '/api/schedule/optimize': (value) =>
    record(value) &&
    record(value.comparison) &&
    metrics(value.comparison.baseline) &&
    metrics(value.comparison.optimized) &&
    delta(value.comparison.delta) &&
    paired(value.gantt, operation) &&
    paired(value.why_late, lateOrder),
  '/api/schedule/simulate': (value) =>
    record(value) &&
    record(value.scenario_inputs) &&
    strings(value.scenario_inputs.down_resource_ids) &&
    strings(value.scenario_inputs.rush_order_ids) &&
    number(value.scenario_inputs.demand_spike_pct) &&
    metrics(value.reference_metrics) &&
    metrics(value.scenario_metrics) &&
    delta(value.delta) &&
    list(value.due_date_impact, impact) &&
    list(value.why_late, lateOrder) &&
    list(value.gantt, operation),
}

function invalidResponse(path: string) {
  return new ApiError(
    `The API response contains invalid data for ${path.split('?')[0]}. Retry, then contact the API administrator if the problem continues.`,
    undefined,
  )
}
