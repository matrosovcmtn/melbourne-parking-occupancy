---
license: cc-by-4.0
language:
  - en
task_categories:
  - time-series-forecasting
  - tabular-regression
tags:
  - parking
  - smart-city
  - urban-mobility
  - melbourne
  - australia
  - occupancy
  - open-data
size_categories:
  - 1M<n<10M
configs:
  - config_name: occupancy
    data_files: data/occupancy_*.parquet
  - config_name: parking_zones
    data_files: data/parking_zones.parquet
---

# Melbourne Parking Occupancy Dataset

1.41 million half-hourly occupancy observations for **536 kerbside parking
zones** in Melbourne, 18 September to 19 November 2026.

The City of Melbourne publishes the **current** status of 6,324 in-ground
parking sensors, and only the current status. Query the API twice and you get
two snapshots; nothing tells you what the street looked like last Tuesday at
18:00. This dataset is that missing axis.

## Configs

| Config | Rows | What it is |
|---|---|---|
| `occupancy` | 1.41 M | One row per zone per 30-minute slot |
| `parking_zones` | 536 | Name, street, coordinates, bay count per zone |

```python
from datasets import load_dataset

occ = load_dataset("matrosovdani/melbourne-parking-occupancy", "occupancy", split="train")
zones = load_dataset("matrosovdani/melbourne-parking-occupancy", "parking_zones", split="train")
```

## Read this before modelling

**Zones are small.** The median zone has 7 bays and 69 zones have one or two.
Occupancy on a two-bay zone takes three values: 0, 50 and 100. Aggregate by
street or by grid cell before fitting anything that assumes a continuous
target.

**86 zones never move.** Their series has zero variance over the whole period:
the sensors are out, or the bays are permanently signed away. They are 16% of
the rows and they will flatter any model scored on all zones at once.
`feed_silent` flags a stricter subset of 16 zones that stopped reporting free
bays entirely.

```python
live = zones.loc[~zones.feed_silent, "id"]
occ = occ[occ.parking_id.isin(live)]
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
moment, computed by the collector.

## Known quirks

Measured on this release. Nothing is cleaned; this is an observational
archive.

**1. `free_spaces` exceeds the zone's bay count in 696 rows (0.05%, 120
zones).** The city adds and removes sensors, and the bay count is today's
value while the row is from the day it was collected. Filter with
`free_spaces <= bays` if an exact denominator matters.

**2. Nothing is negative and nothing is out of range.** `occupancy_rate` stays
within 0-100 across all 1.41 million rows.

**3. Slot boundaries are exact after 2026-11-12, approximate before.** Earlier
rows carry the moment of collection and drift a few seconds inside the slot.
Floor to 30 minutes if you need an exact grid.

## Shape of the data

Occupancy averages 44.4% and swings from 32% at 04:00 to 56% at 19:00
Melbourne time. Exactly zero appears in 17.5% of rows and exactly 100% in
9.7%: small zones hit both ends often, so treat the target as bounded rather
than Gaussian.

## Licence and attribution

Source: **City of Melbourne**, On-street Parking Bay Sensors, licensed
**CC BY 4.0**. This dataset carries the same licence.

Cite both:

```
Melbourne Parking Occupancy (2026). Collected by ParkOut from City of
Melbourne On-street Parking Bay Sensors (CC BY 4.0).
https://github.com/matrosovcmtn/melbourne-parking-occupancy
```

## Related

[Moscow Parking Occupancy](https://huggingface.co/datasets/matrosovdani/moscow-parking-occupancy):
same collector, 5.17 million rows since March 2025, 213 municipal car parks.
The two differ in kind, not only in city: Moscow publishes car parks with a
declared capacity, Melbourne publishes individual kerbside sensors.
