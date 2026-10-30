#!/usr/bin/env bash
# Rebuild the fabrication outputs (gerbers, drill, BOM, CPL) for JLCPCB.
set -euo pipefail
cd "$(dirname "$0")/.."

PROJECT=kvm-board
FAB=fab
rm -rf "$FAB"
mkdir -p "$FAB/gerbers"

kicad-cli pcb export gerbers \
  --layers "F.Cu,B.Cu,F.Paste,B.Paste,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts" \
  -o "$FAB/gerbers/" "$PROJECT.kicad_pcb"

kicad-cli pcb export drill --format excellon --excellon-units mm --excellon-separate-th \
  -o "$FAB/gerbers/" "$PROJECT.kicad_pcb"

(cd "$FAB/gerbers" && zip -q -r ../"$PROJECT-gerbers.zip" .)

kicad-cli pcb export pos --format csv --units mm --side front \
  -o "$FAB/pos_kicad.csv" "$PROJECT.kicad_pcb"

python3 scripts/make_jlc_files.py
ls -l "$FAB"
