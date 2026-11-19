# --- CELL 1 ---
import pandas as pd, numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

import glob, os

# Файлы ищутся рекурсивно, а не задаются путём. Kaggle монтирует подключённые
# датасеты не всегда одинаково: бывает /kaggle/input/<slug>/, бывает глубже.
# Заодно это работает и с клоном репозитория, где occupancy лежит помесячно.
ROOTS = ["/kaggle/input", "data", "."]
occ_files, zones_file = [], None
for root in ROOTS:
    if not os.path.isdir(root):
        continue
    occ_files = sorted(glob.glob(f"{root}/**/occupancy*.parquet", recursive=True))
    found = sorted(glob.glob(f"{root}/**/parking_zones.parquet", recursive=True))
    zones_file = found[0] if found else None
    if occ_files and zones_file:
        break
if not (occ_files and zones_file):
    listing = {r: sorted(os.listdir(r))[:10] for r in ROOTS if os.path.isdir(r)}
    raise FileNotFoundError(f"данные не найдены; что лежит рядом: {listing}")

print(f"найдено файлов занятости: {len(occ_files)}")
occ = pd.concat((pd.read_parquet(f) for f in occ_files), ignore_index=True)
zones = pd.read_parquet(zones_file)

print(f"occupancy    : {len(occ):,} rows, {occ.time.min()} .. {occ.time.max()}")
print(f"parking_zones: {len(zones)} zones, {int(zones.bays.sum()):,} bays")
occ.head()

# --- CELL 2 ---
# The rhythm is a local-time phenomenon; timestamps are UTC.
t = occ.time.dt.tz_convert("Australia/Melbourne")
occ["dow"], occ["hour"] = t.dt.dayofweek, t.dt.hour

rhythm = occ.groupby(["dow", "hour"]).occupancy_rate.mean().unstack("hour")

RAMP = ["#fde4d5","#fbd3bd","#f9c1a3","#f7ae88","#f59a6d","#f28653","#eb6834",
        "#da5a2a","#c44e22","#ad431c","#943716","#7c2d11","#65240d"]
cmap = LinearSegmentedColormap.from_list("seq_orange", RAMP)

fig, ax = plt.subplots(figsize=(12, 3.6))
im = ax.imshow(rhythm.values, aspect="auto", cmap=cmap, interpolation="nearest")
ax.set_yticks(range(7), ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"])
ax.set_xticks(range(0, 24, 3), [f"{h:02d}" for h in range(0, 24, 3)])
ax.set_xlabel("hour of day, Melbourne time")
ax.set_title("Mean occupancy by weekday and hour", loc="left", fontsize=13)
for s in ax.spines.values(): s.set_visible(False)
ax.tick_params(length=0)
fig.colorbar(im, ax=ax, pad=0.01).set_label("% occupied")
plt.tight_layout(); plt.show()

# The peak is in the evening, not at the morning commute: 19:00 and 20:00 are
# the busiest hours of the week, while 08:00 sits near the daily minimum.

# --- CELL 3 ---
# Zones are small, and that shapes everything downstream. The median zone has
# 7 bays; 69 zones have one or two, where occupancy can only be 0, 50 or 100.
small = zones[zones.bays <= 2]
print(f"{len(small)} zones of {len(zones)} have 1-2 bays")

tiny = occ[occ.parking_id.isin(small.id)].occupancy_rate.value_counts(normalize=True)
big = occ[occ.parking_id.isin(zones.loc[zones.bays >= 20, "id"])].occupancy_rate

fig, axes = plt.subplots(1, 2, figsize=(12, 3.2))
axes[0].bar(tiny.index[:6], tiny.values[:6] * 100, color="#eb6834", width=12)
axes[0].set_title("Zones with 1-2 bays: a handful of values", loc="left", fontsize=12)
axes[0].set_ylabel("% of rows"); axes[0].set_xlabel("occupancy_rate")
axes[1].hist(big, bins=40, color="#eb6834")
axes[1].set_title("Zones with 20+ bays: a continuous target", loc="left", fontsize=12)
axes[1].set_xlabel("occupancy_rate")
for ax in axes:
    for s in ("top", "right"): ax.spines[s].set_visible(False)
plt.tight_layout(); plt.show()

# Aggregate by street or by grid cell before fitting anything that assumes a
# continuous target, or restrict to the larger zones.

# --- CELL 4 ---
# City-wide average over the last two weeks. Deliberately not a single zone:
# picking one is cherry-picking, and 86 zones never move at all.
since = occ.time.max() - pd.Timedelta(days=14)
recent = occ[occ.time >= since].copy()
recent["slot"] = recent.time.dt.floor("30min").dt.tz_convert("Australia/Melbourne")
city = recent.groupby("slot").occupancy_rate.mean()

fig, ax = plt.subplots(figsize=(12, 3.2))
ax.plot(city.index, city.values, color="#eb6834", linewidth=2)
ax.fill_between(city.index, city.values, color="#eb6834", alpha=0.12)

# Shade weekends so the weekly cycle is readable without counting days
for day, grp in city.groupby(city.index.normalize()):
    if day.dayofweek >= 5:
        ax.axvspan(day, day + pd.Timedelta(days=1), color="#0b0b0b", alpha=0.045, lw=0)

ax.set_ylim(0, 100)
ax.set_ylabel("% occupied")
ax.set_title(f"Average across all {len(zones)} zones, last two weeks (weekends shaded)",
             loc="left", fontsize=13)
for sp in ("top", "right"): ax.spines[sp].set_visible(False)
plt.tight_layout(); plt.show()

# --- CELL 5 ---
# How predictable is it? Two naive baselines on a 14-day holdout. The window is
# shorter than you would normally pick because the series is only two months
# long, and a week of it is missing in November.
occ["slot"] = occ.time.dt.floor("30min")
wide = occ.pivot_table(index="slot", columns="parking_id",
                       values="occupancy_rate", aggfunc="mean")
wide = wide.asfreq("30min")                      # make gaps explicit
print(f"grid: {wide.shape[0]:,} slots x {wide.shape[1]} zones")

cutoff = wide.index.max() - pd.Timedelta(days=14)
truth = wide.loc[wide.index > cutoff]

for label, periods in [("30 minutes ago", 1), ("same time last week", 336)]:
    pred = wide.shift(periods).loc[truth.index]
    mae = (truth - pred).abs().stack().mean()
    print(f"MAE, {label:22}: {mae:5.2f} percentage points")

# Persistence wins by a wide margin here, and that is worth pausing on: in the
# sibling Moscow dataset the ordering is reversed, because large car parks have
# a strong weekly rhythm while a two-bay kerbside zone flips between discrete
# states that last week's value cannot anticipate. Beat persistence first; the
# weekly baseline is weak on this data and easy to beat for the wrong reason.

# --- CELL 6 ---
mean_occ = occ.groupby("parking_id").occupancy_rate.mean()
geo = zones.set_index("id").join(mean_occ.rename("mean_occ")).dropna(subset=["mean_occ"])

fig, ax = plt.subplots(figsize=(7.5, 7.5))
sc = ax.scatter(geo.longitude, geo.latitude, c=geo.mean_occ, cmap=cmap,
                s=geo.bays * 1.6 + 10, edgecolor="white", linewidth=0.6)
ax.set_title("Kerbside zones: size = bays, colour = mean occupancy",
             loc="left", fontsize=13)
ax.set_xlabel("longitude"); ax.set_ylabel("latitude")
for s in ("top", "right"): ax.spines[s].set_visible(False)
fig.colorbar(sc, ax=ax, pad=0.02).set_label("% occupied")
plt.tight_layout(); plt.show()
