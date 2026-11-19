#!/usr/bin/env python3
"""Приводит выгрузку из базы к публикуемой схеме Мельбурна.

База у ParkOut общая на все города, и колонки в ней заведены под Москву:
метро, места для людей с ограниченными возможностями, русские названия. Для
Мельбурна часть из них не имеет смысла, и публиковать их пустыми значит врать
о составе данных:

  subway_ru, subway_en          пусты у всех 536 зон
  handicapped_spaces            ноль у всех: датчики города не различают
  free_handicapped_spaces       тип места, в выдаче такого поля нет вовсе
  name_ru, address_street_ru    машинный перевод английских названий

Английские названия переименованы в name и street: датасет англоязычный, и
суффикс _en в нём лишний.

Запуск:
    python scripts/shape_for_publication.py --in data-raw --out data
"""
import argparse
import pathlib
import sys

import pandas as pd

SPOT_COLUMNS = {
    "id": "id",
    "external_id": "zone_id",
    "name_en": "name",
    "address_street_en": "street",
    "latitude": "latitude",
    "longitude": "longitude",
    "total_spaces": "bays",
    "last_free_at": "last_free_at",
    "feed_silent": "feed_silent",
}
OCCUPANCY_COLUMNS = ["time", "parking_id", "free_spaces", "occupancy_rate"]


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--in", dest="src", type=pathlib.Path, required=True)
    p.add_argument("--out", dest="dst", type=pathlib.Path, required=True)
    args = p.parse_args()
    args.dst.mkdir(parents=True, exist_ok=True)

    spots = pd.read_parquet(args.src / "parking_spots.parquet")
    missing = [c for c in SPOT_COLUMNS if c not in spots.columns]
    if missing:
        print(f"в выгрузке нет колонок: {missing}", file=sys.stderr)
        return 1
    spots = spots[list(SPOT_COLUMNS)].rename(columns=SPOT_COLUMNS)
    spots.to_parquet(args.dst / "parking_zones.parquet", compression="zstd", index=False)
    print(f"parking_zones.parquet: {len(spots)} зон, колонок {len(spots.columns)}")

    total = 0
    for src in sorted(args.src.glob("occupancy_*.parquet")):
        df = pd.read_parquet(src)[OCCUPANCY_COLUMNS]
        out = args.dst / src.name
        df.to_parquet(out, compression="zstd", index=False)
        total += len(df)
        print(f"{out.name}: {len(df):,} строк")
    print(f"итого {total:,} строк")
    return 0


if __name__ == "__main__":
    sys.exit(main())
