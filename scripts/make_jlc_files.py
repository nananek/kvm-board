"""Create JLCPCB-format BOM / CPL from design.py and the KiCad placement file."""

import csv
import math
import os
import sys
from collections import OrderedDict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from design import PARTS  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAB = os.path.join(ROOT, "fab")

# JLCPCB places parts using the orientation of the part in their own library.
# These offsets align KiCad footprints with the JLC library. The SOT-23-6
# offset includes a further 90-degree counterclockwise placement adjustment.
#
# The USB-C receptacle (C165948) needs no rotation offset: its mouth is on the
# same side as the SMT pads, so a +180 correction turns the mouth into the board
# and leaves the pads about 6.5 mm away.  Its JLC origin is, however, 1.571 mm
# closer to the pads than the KiCad footprint origin, so it gets a position
# offset along the connector axis instead.
USB_C_FOOTPRINT = "USB_C_Receptacle_HRO_TYPE-C-31-M-12"
USB_C_POSITION_OFFSET = 1.571

ROTATION_OFFSETS = (
    ("SO-16_3.9x9.9mm_P1.27mm", 270),
    ("SO-8_3.9x4.9mm_P1.27mm", 270),
    ("SOT-23-6", 270),
)


def rotation_offset(footprint):
    for prefix, offset in ROTATION_OFFSETS:
        if footprint == prefix:
            return offset
    return 0


def position_offset(footprint, rotation):
    """Return the JLC-origin correction in CPL coordinates (Y up)."""
    if footprint != USB_C_FOOTPRINT:
        return 0.0, 0.0
    # Move the JLC origin outward along the connector axis.  In KiCad board
    # coordinates the local (0, -offset) vector maps to (-d sin t, -d cos t);
    # the CPL Y axis is inverted relative to KiCad, hence the +cos term.
    rad = math.radians(rotation)
    return (-USB_C_POSITION_OFFSET * math.sin(rad),
            USB_C_POSITION_OFFSET * math.cos(rad))


def clean_fp(fp):
    return fp.split(":", 1)[-1]


def write_bom():
    groups = OrderedDict()
    for part in PARTS:
        key = (part["value"], clean_fp(part["fp"]), part["lcsc"])
        groups.setdefault(key, []).append(part["ref"])
    path = os.path.join(FAB, "bom_jlcpcb.csv")
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Comment", "Designator", "Footprint", "LCSC Part #"])
        for (value, fp, lcsc), refs in groups.items():
            w.writerow([value, ",".join(refs), fp, lcsc])
    print("wrote", path)


def write_cpl():
    src = os.path.join(FAB, "pos_kicad.csv")
    out = os.path.join(FAB, "cpl_jlcpcb.csv")
    with open(src, newline="") as fi, open(out, "w", newline="") as fo:
        r = csv.DictReader(fi)
        w = csv.writer(fo)
        w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
        for row in r:
            # pos export uses the drill/place origin (bottom-left), so Y is
            # already 0..27 with the same origin as the gerbers
            kicad_rot = float(row["Rot"])
            rot = (kicad_rot + rotation_offset(row["Package"])) % 360.0
            dx, dy = position_offset(row["Package"], kicad_rot)
            x = float(row["PosX"]) + dx
            y = float(row["PosY"]) + dy
            w.writerow([row["Ref"], f"{x:.4f}", f"{y:.4f}", "Top", f"{rot:.1f}"])
    print("wrote", out)


if __name__ == "__main__":
    write_bom()
    write_cpl()
