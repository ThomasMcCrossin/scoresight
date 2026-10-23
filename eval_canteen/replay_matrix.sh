#!/bin/bash
# Replay the 10:10 hour's incidents on two builds, one run at a time.
#
# The windows are chosen so each incident is covered by one run and the runs
# are short enough to finish in reasonable time; the feed's -re pacing is
# slower than real time when the host is busy.
#
#   incident a + home 6/7        330-660    (the clock frozen at 5:15)
#   incident b                   660-850    (final, then the new-game board)
#   incident c                   1010-1070  (the clock set up before the game)
#   away 1 and 2                 1250-1460
#   away 3                       1780-1840
#   away 4                       2210-2260
#   home 5 (09:10 clip)          3400-3600
#
# Usage: replay_matrix.sh <out-dir> [fork|upstream|both]
set -u
OUT=${1:?usage: replay_matrix.sh <out-dir> [fork|upstream|both]}
WHICH=${2:-both}
ROOT=/home/canteenhub/worktrees/scoresight/qualify
UPSTREAM=/home/canteenhub/worktrees/scoresight/upstream-0388a1a
CLIP10=/home/canteenhub/.local/share/canteen-ops/scoreboard-camera/crop/20261023T101023.mkv
CLIP09=/home/canteenhub/.local/share/canteen-ops/scoreboard-camera/crop/20261023T091022.mkv

run() { # build name clip start duration
  echo "[matrix] $2 ($1) $(date +%H:%M:%S)"
  nice -n 15 "$ROOT/.venv/bin/python" "$ROOT/eval_canteen/replay_1010.py" \
    --build "$1" --variant filtered --clip "$3" --start "$4" --duration "$5" \
    --name "$2" --out "$OUT" || echo "[matrix] FAILED $2"
}

for build in $( [ "$WHICH" = both ] && echo "fork upstream" || echo "$WHICH" ); do
  if [ "$build" = fork ]; then B=$ROOT; else B=$UPSTREAM; fi
  run "$B" "${build}_a_330_660"   "$CLIP10" 330  330
  run "$B" "${build}_b_660_850"   "$CLIP10" 660  190
  run "$B" "${build}_c_1010_1070" "$CLIP10" 1010 60
  run "$B" "${build}_d12_1250_1460" "$CLIP10" 1250 210
  run "$B" "${build}_d3_1780_1840" "$CLIP10" 1780 60
  run "$B" "${build}_d4_2210_2260" "$CLIP10" 2210 50
  run "$B" "${build}_d5_3400_3600" "$CLIP09" 3400 200
done
echo "[matrix] done $(date +%H:%M:%S)"
