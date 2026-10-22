#!/bin/bash
# Scaffold a 3D lyric-video project from the engine template.
# usage: new_project.sh /path/to/project
set -e
SKILL="$(cd "$(dirname "$0")/.." && pwd)"
DST="$1"; [ -z "$DST" ] && { echo "usage: new_project.sh DIR"; exit 1; }
mkdir -p "$DST"
cp -R "$SKILL/assets/template/." "$DST/"
mkdir -p "$DST/work" "$DST/renders" "$DST/assets/audio"
NAME="$(basename "$DST")"
printf '{\n  "id": "%s",\n  "name": "%s"\n}\n' "$NAME" "$NAME" > "$DST/meta.json"
python3 "$SKILL/scripts/fontjson.py" "$DST"
echo "project ready: $DST  (next: analyze_song.py, song.json, lyrics.txt, prep.py)"
