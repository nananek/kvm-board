#!/usr/bin/env bash
# Rebuild the fabrication outputs (gerbers, drill, BOM, CPL) for JLCPCB.
set -euo pipefail
cd "$(dirname "$0")/.."

PROJECT=serial-km-emulator
FAB=fab
rm -rf "$FAB"
mkdir -p "$FAB/gerbers"

kicad-cli pcb export gerbers \
  --layers "F.Cu,B.Cu,F.Paste,B.Paste,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts" \
  --use-drill-file-origin \
  -o "$FAB/gerbers/" "$PROJECT.kicad_pcb"

kicad-cli pcb export drill --format excellon --excellon-units mm --excellon-separate-th \
  --drill-origin plot \
  -o "$FAB/gerbers/" "$PROJECT.kicad_pcb"

(cd "$FAB/gerbers" && python3 -c '
import glob, os, sys, zipfile
with zipfile.ZipFile(sys.argv[1], "w", zipfile.ZIP_DEFLATED) as z:
    for path in sorted(glob.glob("*")):
        if os.path.isfile(path):
            z.write(path, path)
' "../$PROJECT-gerbers.zip")

kicad-cli pcb export pos --format csv --units mm --side front --use-drill-file-origin \
  -o "$FAB/pos_kicad.csv" "$PROJECT.kicad_pcb"

python3 scripts/make_jlc_files.py
ls -l "$FAB"
