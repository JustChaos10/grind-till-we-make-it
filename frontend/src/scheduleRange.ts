/** Determine the timeline extent without spreading an unbounded operation list into a call. */
export function scheduleEndHour(operations: readonly { end_hour: number }[]): number {
  return operations.reduce((maximum, operation) => Math.max(maximum, operation.end_hour), 24)
}

type TimeInterval = { start_hour: number; end_hour: number }

export function layoutScheduleRow<T extends TimeInterval>(items: readonly T[], maxHour: number) {
  const laneEnds: number[] = []
  const bars = [...items]
    .sort((a, b) => a.start_hour - b.start_hour || a.end_hour - b.end_hour)
    .map((item) => {
      const availableLane = laneEnds.findIndex((end) => end <= item.start_hour)
      const slot = availableLane === -1 ? laneEnds.length : availableLane
      laneEnds[slot] = item.end_hour
      const left = Math.max(0, (item.start_hour / maxHour) * 100)
      const width = (Math.max(0, item.end_hour - item.start_hour) / maxHour) * 100
      return { item, slot, left, width: Math.min(width, 100 - left) }
    })

  return { bars, laneCount: laneEnds.length }
}
