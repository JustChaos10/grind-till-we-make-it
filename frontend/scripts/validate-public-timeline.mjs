import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { layoutScheduleRow, scheduleEndHour } from '../src/scheduleRange.ts'

const dataset = JSON.parse(readFileSync(process.argv[2], 'utf8'))
const rows = Object.entries(dataset)
assert.equal(rows.length, 56)
let count = 0
let overlapRows = 0

for (const [name, observations] of rows) {
  assert.ok(observations.length > 0, name)
  assert.equal(new Set(observations.map((record) => record.id)).size, observations.length, name)
  const endHour = scheduleEndHour(observations)
  const { bars, laneCount } = layoutScheduleRow([...observations].reverse(), endHour)
  assert.equal(bars.length, observations.length, name)
  const edges = []
  const lastEnds = new Map()
  for (const { item, slot, left, width } of bars) {
    assert.ok(item.start_hour >= 0 && item.end_hour > item.start_hour, name)
    assert.ok((lastEnds.get(slot) ?? 0) <= item.start_hour, name)
    assert.ok(width > 0 && left >= 0 && left + width <= 100 + 1e-9, name)
    assert.ok(Math.abs((left / 100) * endHour - item.start_hour) < 1e-9, name)
    assert.ok(Math.abs(((left + width) / 100) * endHour - item.end_hour) < 1e-9, name)
    lastEnds.set(slot, item.end_hour)
    edges.push([item.start_hour, 1], [item.end_hour, -1])
  }
  let peak = 0
  let concurrent = 0
  for (const [, change] of edges.sort(([a, deltaA], [b, deltaB]) => a - b || deltaA - deltaB)) {
    concurrent += change
    peak = Math.max(peak, concurrent)
  }
  assert.equal(laneCount, peak, name)
  count += bars.length
  if (peak > 1) overlapRows += 1
}

console.log(`PASS: ${count} observed intervals in ${rows.length} rows, ${overlapRows} with overlaps`)
