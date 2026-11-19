"""Обложка датасета: недельный ритм занятости. Тепловая карта час × день недели.

Форма та же, что у московского датасета: непрерывная величина по двум
циклическим осям. Цвет другой намеренно. Правило палитры: когда рядом два
последовательных контекста, второй берёт следующий слот категориальной темы,
то есть оранжевый, каждый своей одно-тоновой шкалой. На странице профиля два
датасета теперь не спутать.

Шкала проверена `dataviz/scripts/validate_palette.js --ordinal`: светлота
монотонна, разброс тона 15°, единый тон. Два оставшихся отказа валидатора
(мелкий шаг светлоты и светлый конец ниже 2:1) относятся к порядковым шкалам,
а не к тепловой карте: последовательной шкале светлый конец разрешено уводить
в фон, и московская синяя даёт ровно те же два отказа.

Запуск:
    python publish/kaggle/cover.py
"""
import glob

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_SOFT = "#52514e"
RAMP = ["#fde4d5", "#fbd3bd", "#f9c1a3", "#f7ae88", "#f59a6d", "#f28653",
        "#eb6834", "#da5a2a", "#c44e22", "#ad431c", "#943716", "#7c2d11", "#65240d"]
cmap = LinearSegmentedColormap.from_list("ofm_orange", RAMP)

occ = pd.concat(
    (pd.read_parquet(f) for f in sorted(glob.glob("data/occupancy_*.parquet"))),
    ignore_index=True,
)
zones = pd.read_parquet("data/parking_zones.parquet")

# Ритм — явление местного времени, а метки времени в UTC.
t = occ.time.dt.tz_convert("Australia/Melbourne")
piv = occ.assign(dow=t.dt.dayofweek, hour=t.dt.hour) \
         .groupby(["dow", "hour"]).occupancy_rate.mean().unstack("hour")
m = piv.values
days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

fig = plt.figure(figsize=(12, 6), dpi=100, facecolor=SURFACE)
ax = fig.add_axes([0.068, 0.20, 0.80, 0.545])
ax.set_facecolor(SURFACE)

# Зазор между ячейками даёт сетку цветом поверхности — она же разделитель
im = ax.imshow(m, aspect="auto", cmap=cmap, vmin=m.min(), vmax=m.max(),
               interpolation="nearest")
ax.set_xticks(np.arange(-0.5, 24, 1), minor=True)
ax.set_yticks(np.arange(-0.5, 7, 1), minor=True)
ax.grid(which="minor", color=SURFACE, linewidth=2)
ax.tick_params(which="minor", length=0)

ax.set_xticks(range(0, 24, 3))
ax.set_xticklabels([f"{h:02d}" for h in range(0, 24, 3)], color=INK_SOFT, fontsize=11)
ax.set_yticks(range(7))
ax.set_yticklabels(days, color=INK_SOFT, fontsize=11)
for s in ax.spines.values():
    s.set_visible(False)
ax.tick_params(length=0, pad=6)
ax.set_xlabel("hour of day, Melbourne time", color=INK_SOFT, fontsize=11, labelpad=9)

fig.text(0.068, 0.895, "Melbourne's kerbs fill in the evening, not the morning",
         color=INK, fontsize=25, fontweight="bold", va="top")
fig.text(0.068, 0.815,
         f"Mean occupancy of {len(zones)} kerbside zones · "
         f"{len(occ)/1e6:.2f}M half-hourly observations · Sep – Nov 2026",
         color=INK_SOFT, fontsize=13, va="top")

cax = fig.add_axes([0.885, 0.20, 0.018, 0.545])
cb = fig.colorbar(im, cax=cax)
cb.outline.set_visible(False)
cb.ax.tick_params(length=0, colors=INK_SOFT, labelsize=10, pad=6)
cb.set_ticks([m.min(), m.max()])
cb.set_ticklabels([f"{m.min():.0f}%", f"{m.max():.0f}%"])
cb.ax.set_title("occupied", color=INK_SOFT, fontsize=10, pad=10, loc="left")

fig.text(0.068, 0.065,
         "github.com/matrosovcmtn/melbourne-parking-occupancy · CC BY 4.0",
         color=INK_SOFT, fontsize=10.5, va="center")

fig.savefig("publish/kaggle/cover.png", facecolor=SURFACE)
print(f"сохранено publish/kaggle/cover.png — пик {m.max():.0f}%, минимум {m.min():.0f}%")
