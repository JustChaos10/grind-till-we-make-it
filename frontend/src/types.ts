/** API response types mirror frontend/docs/API_CONTRACT_AND_METRICS.md. */
export type Queue = {
  stage: string
  queue_depth: number
  avg_wip_age_hours: number
}

export type Board = {
  total_wip_orders: number
  avg_wip_age_hours: number
  queues: Queue[]
  active_bottleneck_alerts: string[]
}

export type Resource = {
  id: string
  name: string
  plant: string
  stage: string
  status: string
}

export type WorkOrder = {
  id: string
  wo_number: string
  sku_code: string
  stage: string
  status: string
  due_date_hours: number
  priority: number
}

export type ScheduledOperation = {
  work_order_id: string
  wo_number: string
  sku_code: string
  resource_id: string
  resource_name: string
  plant: string
  stage: string
  start_hour: number
  end_hour: number
  batch_id: string | null
  is_late: boolean
  delay_reason: string | null
}

export type Metrics = {
  late_orders: number
  avg_wip_age_hours: number
  throughput: number
  throughput_horizon_hours: number
  furnace_batch_efficiency_pct: number
  makespan_hours: number
  bottleneck_resource_id: string | null
  resource_busy_hours: Record<string, number>
  weighted_tardiness_hours: number
  schedule_version_id?: string
}

export type LateOrder = {
  work_order_id: string
  wo_number: string
  due_date_hours: number
  completion_hours: number
  delay_hours: number
  priority: number
  explanation: string
}

export type OptimizeResponse = {
  comparison: {
    baseline: Metrics & { schedule_version_id: string }
    optimized: Metrics & { schedule_version_id: string }
    delta: {
      late_orders: number
      avg_wip_age_hours: number
      throughput: number
      furnace_batch_efficiency_pct: number
    }
  }
  gantt: { baseline: ScheduledOperation[]; optimized: ScheduledOperation[] }
  why_late: { baseline: LateOrder[]; optimized: LateOrder[] }
}

export type ScenarioRequest = {
  down_resource_ids: string[]
  rush_order_ids: string[]
  demand_spike_pct: number
  time_limit_seconds: number
}

export type DueDateImpact = {
  work_order_id: string
  wo_number: string
  due_date_before_hours: number
  due_date_scenario_hours: number
  completion_before_hours: number
  completion_scenario_hours: number
  completion_delta_hours: number
  late_before: boolean
  late_scenario: boolean
  delay_delta_hours: number
}

export type ScenarioResponse = {
  scenario_inputs: {
    down_resource_ids: string[]
    rush_order_ids: string[]
    demand_spike_pct: number
  }
  reference_metrics: Metrics
  scenario_metrics: Metrics
  delta: {
    late_orders: number
    avg_wip_age_hours: number
    throughput: number
    bottleneck_before: string | null
    bottleneck_after: string | null
  }
  due_date_impact: DueDateImpact[]
  why_late: LateOrder[]
  gantt: ScheduledOperation[]
}

export type CatalogResponse = { resources: Resource[]; work_orders: WorkOrder[] }
