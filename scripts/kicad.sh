#!/usr/bin/env bash
# Run a command inside the KiCad 10 container with this repository at /work.
#
# Examples:
#   ./scripts/kicad.sh ./scripts/export_fab.sh
#   ./scripts/kicad.sh kicad-cli pcb drc --severity-all serial-km-emulator.kicad_pcb
#
# Override the image with KICAD_IMAGE (default: kicad/kicad:10.0).  If the
# current user cannot write to /work inside the container (rootless Docker
# maps the bind mount to root), fall back to running as root.
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/.." && pwd)
IMAGE=${KICAD_IMAGE:-kicad/kicad:10.0}

if docker run --rm --user "$(id -u):$(id -g)" -v "$ROOT:/work" "$IMAGE" test -w /work >/dev/null 2>&1; then
  exec docker run --rm --user "$(id -u):$(id -g)" -e HOME=/tmp -v "$ROOT:/work" -w /work "$IMAGE" "$@"
else
  exec docker run --rm --user 0:0 -e HOME=/tmp -v "$ROOT:/work" -w /work "$IMAGE" "$@"
fi
