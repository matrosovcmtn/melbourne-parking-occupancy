#!/usr/bin/env bash
#
# Обновление датасета: выгрузка из базы, приведение к публикуемой схеме,
# коммит изменившихся файлов.
#
# Запускать на сервере ParkOut, где живёт база. Переменные подключения берутся
# из /etc/parkout/dataset.env, как и у московского датасета.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_DIR"

[ -n "${DATABASE_URL:-}" ] || { echo "не задан DATABASE_URL" >&2; exit 1; }

echo "выгрузка из базы..."
"$REPO_DIR/.venv/bin/python" scripts/export_from_db.py \
    --city melbourne --output-dir "$REPO_DIR/data-raw" --verbose

echo "приведение к публикуемой схеме..."
"$REPO_DIR/.venv/bin/python" scripts/shape_for_publication.py \
    --in "$REPO_DIR/data-raw" --out "$REPO_DIR/data"

if git diff --quiet -- data; then
    echo "данные не изменились, коммит не нужен"
    exit 0
fi

git add data
git -c user.name="Parkout Dataset Bot" -c user.email="dataset-bot@parkout.ru" \
    commit -q -m "data: refresh $(date -u +%F)"
git push origin main
echo "готово"
