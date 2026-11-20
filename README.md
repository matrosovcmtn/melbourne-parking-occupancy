# Melbourne Parking Occupancy

> Open dataset of 30-minute on-street parking occupancy for 536 kerbside zones in Melbourne, Australia.

**1.41 million** half-hourly observations · **536 zones** covering 5,804 bays · 18 Sep – 19 Nov 2026 · 1.9 MB of Parquet

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.24405345.svg)](https://doi.org/10.5281/zenodo.24405345)
[![License: CC BY 4.0](https://img.shields.io/badge/Data%20License-CC%20BY%204.0-lightgrey.svg)](DATA_LICENSE)
[![Kaggle](https://img.shields.io/badge/Kaggle-dataset-20BEFF.svg)](https://www.kaggle.com/datasets/danilmatrosov/melbourne-parking-occupancy)
[![Hugging Face](https://img.shields.io/badge/%F0%9F%A4%97%20Hugging%20Face-dataset-FFD21E.svg)](https://huggingface.co/datasets/matrosovdani/melbourne-parking-occupancy)

## Why this exists

The City of Melbourne publishes the **current** status of 6,324 in-ground parking
sensors, and only the current status. Query the API twice and you get two
snapshots; nothing tells you what the street looked like last Tuesday at 18:00.

This dataset is that missing axis. A collector polls the city's feed on a
30-minute grid, aggregates bays into the city's own zones, and keeps the result.
Everything else here (coordinates, street names, zone capacity) comes straight
from the city.

If you need live data, use the [source](https://data.melbourne.vic.gov.au/explore/dataset/on-street-parking-bay-sensors/information/).
If you need history, there was nowhere to get it until now.

## Files

| file | what is in it | rows | size |
|---|---|---|---|
| `data/occupancy_YYYY-MM.parquet` | one row per zone per half-hour slot | 1,413,875 | 1.8 MB |
| `data/parking_zones.parquet` | static metadata: name, street, coordinates, capacity | 536 | 31 KB |

```python
import pandas as pd, glob

occ = pd.concat(map(pd.read_parquet, sorted(glob.glob("data/occupancy_*.parquet"))))
zones = pd.read_parquet("data/parking_zones.parquet")
busy = occ.merge(zones, left_on="parking_id", right_on="id")
```

### Columns

`occupancy_*.parquet`

| column | type | meaning |
|---|---|---|
| `time` | timestamp, UTC | start of the half-hour slot |
| `parking_id` | int32 | zone key, joins to `parking_zones.id` |
| `free_spaces` | int32 | bays reported unoccupied in that zone |
| `occupancy_rate` | float64 | percent of the zone's bays occupied, 0–100 |

`parking_zones.parquet`

| column | type | meaning |
|---|---|---|
| `id` | int32 | join key |
| `zone_id` | int32 | the city's own zone number, as in the source feed |
| `name` | string | street plus zone number, e.g. `Argyle Place North, zone 7001` |
| `street` | string | street only; empty for 9 zones the city leaves unnamed |
| `latitude`, `longitude` | float64 | centre of the zone, averaged over its bays |
| `bays` | int32 | number of sensors in the zone |
| `last_free_at` | timestamp | last slot where the zone reported a free bay |
| `feed_silent` | bool | zone has not reported a free bay in the last 30 days |

## Read this before modelling

**Zones are small.** The median zone has 7 bays and 69 zones have one or two.
Occupancy on a two-bay zone takes three values: 0, 50 and 100. Aggregate by
street or by grid cell before fitting anything that assumes a continuous target.

**86 zones never move.** Their series has zero variance over the whole period:
the sensors are out, or the bays are permanently signed away. They are 16% of
the rows and they will flatter any model that is scored on all zones at once.
`feed_silent` flags a stricter subset of 16 zones that stopped reporting free
bays entirely.

```python
live = zones.loc[~zones.feed_silent, "id"]
occ = occ[occ.parking_id.isin(live)]      # drops the 16 clearly dead feeds
```

**There is a seven-day hole.** No data between 2026-11-05 09:55 and 2026-11-12
07:00 UTC. A database constraint requiring half-hour-aligned timestamps was
deployed ahead of the collector that produces them, every write was rejected
for a week, and the collector logged success throughout. The source publishes
current state only, so the week cannot be recovered. Two shorter gaps of 1 and
1.5 hours sit in early October. In total 332 slots of an expected 2,972 are
missing.

**Occupancy is derived, not reported.** The city reports each bay as occupied
or not. `occupancy_rate` is the share of occupied bays in the zone at that
moment, computed by the collector. `free_spaces` is the count behind it.

## Known quirks

Measured on this release. Nothing is cleaned; this is an observational archive.

**1. `free_spaces` exceeds the zone's bay count in 696 rows (0.05%, 120 zones).**
The city adds and removes sensors, and the zone's bay count is today's value
while the row is from the day it was collected. Filter with
`free_spaces <= bays` if an exact denominator matters.

**2. Nothing is negative and nothing is out of range.** `occupancy_rate` stays
within 0–100 across all 1.41 million rows. Melbourne's feed is markedly cleaner
than the Moscow one in the [sibling dataset](https://github.com/matrosovcmtn/moscow-parking-occupancy),
where the same collector produces 19,785 negative values from a different
upstream quirk.

**3. Slot boundaries are exact after 2026-11-12, approximate before.** Early
rows carry the moment of collection, which drifts a few seconds inside the
slot. Floor to 30 minutes if you need an exact grid: `occ.time.dt.floor("30min")`.

## Shape of the data

Occupancy averages 44.4% across the period and swings from 32% at 04:00 to 56%
at 19:00 Melbourne time. Exactly zero occupancy appears in 17.5% of rows and
exactly 100% in 9.7%: small zones hit both ends often, so treat the target as
bounded rather than Gaussian.

## Refreshing

```bash
python scripts/export_from_db.py --city melbourne --output-dir data-raw
python scripts/shape_for_publication.py --in data-raw --out data
```

The export reads the ParkOut collector's TimescaleDB. The second step drops the
columns that are empty for Melbourne and renames the English ones, so the
published schema matches what the city actually provides.

## Licence and attribution

Source data: **City of Melbourne**, [On-street Parking Bay Sensors](https://data.melbourne.vic.gov.au/explore/dataset/on-street-parking-bay-sensors/information/),
licensed **CC BY 4.0**.

This dataset: **CC BY 4.0** (`data/`), MIT for the code (`scripts/`). See
[DATA_LICENSE](DATA_LICENSE) and [LICENSE-CODE](LICENSE-CODE).

If you use it, cite both this dataset and the city's feed it derives from:

```
Matrosov, D. (2026). Melbourne Parking Occupancy Dataset [Data set]. Zenodo.
https://doi.org/10.5281/zenodo.24405345
Derived from City of Melbourne, On-street Parking Bay Sensors (CC BY 4.0).
```

```bibtex
@dataset{matrosov2026melbourneparking,
  author    = {Matrosov, Danil},
  title     = {Melbourne Parking Occupancy Dataset},
  year      = {2026},
  publisher = {Zenodo},
  doi       = {10.5281/zenodo.24405345},
  url       = {https://doi.org/10.5281/zenodo.24405345}
}
```

That DOI follows the newest version. For a reproducible snapshot cite the version
DOI: the release of 20 November 2026 is [`10.5281/zenodo.24405346`](https://doi.org/10.5281/zenodo.24405346).

## Related

[Moscow Parking Occupancy](https://github.com/matrosovcmtn/moscow-parking-occupancy):
same collector, 5.17 million rows since March 2025, 213 municipal car parks.
The two differ in kind, not only in city: Moscow publishes car parks with a
declared capacity, Melbourne publishes individual kerbside sensors.
