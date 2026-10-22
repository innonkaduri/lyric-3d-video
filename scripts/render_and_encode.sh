#!/bin/bash
# Render the project at delivery quality, then make the upload copies.
# usage: render_and_encode.sh PROJECT_DIR NAME   (e.g. ... selfaware_v6)
# -> renders/NAME_master.mp4 (huge: grain), NAME_upload.mp4 (<30 MB, 2-pass), NAME_upload_nomusic.mp4
set -e
P="$1"; N="$2"; cd "$P"
npx hyperframes@0.8.161 check . 2>&1 | grep -E "error\(s\)" || true
HF_CAPTURE_PARALLEL_STREAM=true npx hyperframes@0.8.161 render . -o "renders/${N}_master.mp4" --quality delivery --fps 30 > "work/render_${N}.log" 2>&1
tail -4 "work/render_${N}.log" | sed 's/\x1b\[[0-9;]*m//g' | head -2
DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "renders/${N}_master.mp4")
# target ~27 MB total: video bitrate = 27MB*8/dur - 192k audio
VB=$(python3 -c "print(int(27*8*1000/float('$DUR') - 192))")
cd renders
ffmpeg -v error -y -i "${N}_master.mp4" -c:v libx264 -preset slow -b:v ${VB}k -pass 1 -passlogfile ../work/p2 -an -f null /dev/null
ffmpeg -v error -y -i "${N}_master.mp4" -c:v libx264 -preset slow -b:v ${VB}k -maxrate $((VB*17/10))k -bufsize $((VB*2))k -pass 2 -passlogfile ../work/p2 -pix_fmt yuv420p -c:a aac -b:a 192k -movflags +faststart "${N}_upload.mp4"
ffmpeg -v error -y -i "${N}_upload.mp4" -c:v copy -an -movflags +faststart "${N}_upload_nomusic.mp4"
rm -f ../work/p2*
ls -la "${N}"_*
