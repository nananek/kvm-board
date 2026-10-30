"""Create JLCPCB-format BOM / CPL from design.py and the KiCad placement file."""

import csv
import os
import sys
from collections import OrderedDict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from design import PARTS  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAB = os.path.join(ROOT, "fab")
BOARD_H = 27.0


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
            y = BOARD_H + float(row["PosY"])  # KiCad Y is negative = up
            rot = float(row["Rot"]) % 360.0
            w.writerow([row["Ref"], f"{float(row['PosX']):.4f}",
                        f"{y:.4f}", "Top", f"{rot:.1f}"])
    print("wrote", out)


if __name__ == "__main__":
    write_bom()
    write_cpl()
