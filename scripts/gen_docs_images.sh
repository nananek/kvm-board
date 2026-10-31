#!/usr/bin/env bash
# Regenerate the board images in docs/ with kicad-cli.
#
# Requires kicad-cli (10.x), python3 with pcbnew, Ghostscript and sed.
# The kicad/kicad:10.0 container has all of them; see AGENT.md.
set -euo pipefail
cd "$(dirname "$0")/.."

PROJECT=serial-km-emulator
WIDTH=1800
# 57.6 mm wide board -> PIXELS_PER_MM = 1800 / 57.6
DPI=$(python3 -c "print(f'{$WIDTH * 25.4 / 57.6:.4f}')")

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

# kicad-cli's PDF export has no page-size option, so make the sheet exactly the
# board size (57.6 x 31.4 mm, see scripts/gen_pcb.py).  The plot then fills the
# page and no drawing sheet is drawn.
sed 's/(paper "A4")/(paper "User" 57.6 31.4)/' "$PROJECT.kicad_pcb" > "$TMP/board.kicad_pcb"
python3 scripts/strip_zones.py "$TMP/board.kicad_pcb" "$TMP/board_routing.kicad_pcb"

plot() {
  local layers=$1 name=$2 board=$3
  shift 3
  kicad-cli pcb export pdf --layers "$layers" -o "$TMP/$name.pdf" "$@" "$board" >/dev/null
  gs -q -dNOPAUSE -dBATCH -sDEVICE=png16m -r"$DPI" \
    -o "docs/$name.png" "$TMP/$name.pdf"
  echo "wrote docs/$name.png"
}

plot "F.Cu,F.SilkS,Edge.Cuts" pcb_top "$TMP/board.kicad_pcb"
plot "B.Cu,B.SilkS,Edge.Cuts" pcb_bottom "$TMP/board.kicad_pcb" --mirror
plot "F.Cu,B.Cu,F.SilkS,Edge.Cuts" pcb_routing "$TMP/board_routing.kicad_pcb"
