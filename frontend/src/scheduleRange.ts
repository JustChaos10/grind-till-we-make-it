/** Determine the timeline extent without spreading an unbounded operation list into a call. */
export function scheduleEndHour(operations: readonly { end_hour: number }[]): number {
  return operations.reduce((maximum, operation) => Math.max(maximum, operation.end_hour), 24)
}
