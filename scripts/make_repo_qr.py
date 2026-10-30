#!/usr/bin/env python3
"""Regenerate scripts/repo_qr.txt (the silkscreen QR code on the back).

This is only needed when the repository URL changes, so it is not part of the
normal board build.  It requires the ``qrcode`` package:

    python3 -m pip install qrcode
    python3 scripts/make_repo_qr.py

The board generator reads the checked-in text file, so building the PCB does
not need the qrcode package.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from design import REPO_URL  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "scripts", "repo_qr.txt")
BORDER = 4
ECC = "M"


def main():
    try:
        import qrcode
        from qrcode.constants import ERROR_CORRECT_M
    except ImportError:
        raise SystemExit("qrcode is required: python3 -m pip install qrcode")

    qr = qrcode.QRCode(error_correction=ERROR_CORRECT_M, box_size=1, border=BORDER)
    qr.add_data(REPO_URL)
    qr.make(fit=True)
    matrix = qr.get_matrix()

    lines = [
        "# QR code for " + REPO_URL,
        f"# {len(matrix)}x{len(matrix)} modules including the {BORDER}-module quiet zone. "
        "1 = dark, 0 = light.",
        "# Regenerate with: python3 scripts/make_repo_qr.py",
    ]
    for row in matrix:
        lines.append("".join("1" if v else "0" for v in row))
    with open(OUT, "w") as f:
        f.write("\n".join(lines) + "\n")
    print("wrote", OUT, f"({len(matrix)}x{len(matrix)}, ECC {ECC})")


if __name__ == "__main__":
    main()
