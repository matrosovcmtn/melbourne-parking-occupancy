# Changelog

All notable changes to this dataset are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
The *schema* follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html);
data refreshes use date-based entries.

---

## [Unreleased]

### Planned
- Weekly refresh on the same schedule as the Moscow dataset
- Per-zone coverage map over time

---

## [1.0.0] — 2026-11-19

First release.

### Added
- 1,413,875 half-hourly occupancy observations for 536 kerbside zones in
  Melbourne, covering 2026-09-18 to 2026-11-19.
- `data/parking_zones.parquet`: zone metadata for all 536 zones — the city's
  zone number, name, street, coordinates, bay count, and a `feed_silent` flag.
- Schema, licence split (CC BY 4.0 for data, MIT for code) and the export and
  shaping scripts that reproduce the published files.

### Notes on the data
- Occupancy is derived, not reported: the city publishes per-bay occupied or
  free, and the share per zone is computed by the collector.
- The city publishes current state only. The time axis is what this dataset
  contributes; it cannot be reconstructed from the source after the fact.
- Four columns present in the collector's database are dropped here because
  they carry nothing for Melbourne: the two metro columns are empty for all
  536 zones, accessible-bay counts are zero everywhere since the sensors do
  not distinguish bay types, and the Russian name columns are machine
  translations of the English ones.

### Known issues
- No data between 2026-11-05 09:55 and 2026-11-12 07:00 UTC. A database
  constraint requiring half-hour-aligned timestamps was deployed ahead of the
  collector that produces them, every write was rejected for a week, and the
  collector reported success in its log throughout. The source publishes
  current state only, so the week is not recoverable. Two shorter gaps of one
  and one and a half hours sit in early October. In total 332 slots of an
  expected 2,972 are missing.
- `free_spaces` exceeds the zone's bay count in 696 rows (0.05%, 120 zones):
  the city adds and removes sensors, and the bay count is today's value while
  the row is from the day it was collected.
- 86 zones have zero variance over the whole period. They are 16% of the rows.
  `feed_silent` flags a stricter subset of 16.
- Timestamps before 2026-11-12 carry the moment of collection and drift a few
  seconds inside the slot; from 2026-11-12 they sit exactly on the grid.
