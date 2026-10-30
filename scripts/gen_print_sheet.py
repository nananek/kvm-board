"""Generate an A4, 1:1 print sheet for checking the board against the case.

The board outline is read from kvm-board.kicad_pcb (Edge.Cuts), then drawn on
an A4 landscape page at exactly 1:1 together with the FRISK case inner tray
outline, dimension lines and a 150 mm scale check.

Everything is written with the standard library so the sheet can be produced
without KiCad: the PDF user space is in millimetres (1 mm = 72/25.4 pt), which
makes the print size independent of the PDF viewer.

Usage:
    python3 scripts/gen_print_sheet.py [output.pdf]
"""

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PCB = os.path.join(ROOT, "kvm-board.kicad_pcb")
DEFAULT_OUT = os.path.join(ROOT, "docs", "print_check_a4.pdf")

MM = 72.0 / 25.4
A4_W, A4_H = 297.0, 210.0

# Board placement on the page (mm, origin at the bottom-left of the board).
BX, BY = 30.0, 112.0
BOARD_W, BOARD_H = 65.4, 31.4
CASE_CLEARANCE = 0.5

# Connector centres in board coordinates (y from the top edge).
J1_Y, J2_Y = 14.0, 5.5
J1_X, J2_X = 3.629, 61.771
SHELL_X, SHELL_Y = 8.94, 7.3  # footprint body before rotation (x, y)


def read_outline(path):
    """Return the Edge.Cuts segments as ((x1, y1), (x2, y2)) tuples."""
    src = open(path, encoding="utf-8").read()
    segs = []
    for m in re.finditer(
        r"\(gr_line\s*\(start\s+([-\d.]+)\s+([-\d.]+)\)\s*"
        r"\(end\s+([-\d.]+)\s+([-\d.]+)\)\s*\(stroke.*?\(layer\s+\"([^\"]+)\"\)",
        src,
        re.S,
    ):
        if m.group(5) != "Edge.Cuts":
            continue
        segs.append(((float(m.group(1)), float(m.group(2))),
                     (float(m.group(3)), float(m.group(4)))))
    if not segs:
        raise SystemExit("no Edge.Cuts segments found in " + path)
    return segs


def read_silk_text(path):
    """Return (text, x, y, size) for the F.SilkS board texts."""
    src = open(path, encoding="utf-8").read()
    out = []
    for m in re.finditer(
        r"\(gr_text\s+\"([^\"]*)\"\s*\(at\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\)\s*"
        r"\(layer\s+\"F\.SilkS\"\).*?\(size\s+([\d.]+)\s+([\d.]+)\)",
        src,
        re.S,
    ):
        if float(m.group(4)) % 360.0 != 0.0:
            continue
        out.append((m.group(1), float(m.group(2)), float(m.group(3)),
                    float(m.group(5))))
    return out


class Sheet:
    """Minimal PDF writer; coordinates are millimetres with y pointing up."""

    def __init__(self, width, height):
        self.w, self.h = width, height
        self.ops = []

    def _num(self, v):
        return ("%.3f" % v).rstrip("0").rstrip(".")

    def line(self, x1, y1, x2, y2, width=0.2, dash=None):
        d = "[%s %s] 0 d" % tuple(self._num(v) for v in dash) if dash else "[] 0 d"
        self.ops.append("%s %s w %s %s m %s %s l S" % (
            d, self._num(width), self._num(x1), self._num(y1),
            self._num(x2), self._num(y2)))

    def rect(self, x, y, w, h, width=0.2, dash=None):
        self.line(x, y, x + w, y, width, dash)
        self.line(x + w, y, x + w, y + h, width, dash)
        self.line(x + w, y + h, x, y + h, width, dash)
        self.line(x, y + h, x, y, width, dash)

    def polyline(self, pts, width=0.2, dash=None):
        for a, b in zip(pts, pts[1:]):
            self.line(a[0], a[1], b[0], b[1], width, dash)

    def text(self, s, x, y, size=3.0, angle=0.0):
        s = s.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")
        if angle:
            import math
            c, sn = math.cos(math.radians(angle)), math.sin(math.radians(angle))
            tm = "%s %s %s %s %s %s Tm" % (
                self._num(c * size), self._num(sn * size),
                self._num(-sn * size), self._num(c * size),
                self._num(x), self._num(y))
        else:
            tm = "%s 0 0 %s %s %s Tm" % (
                self._num(size), self._num(size), self._num(x), self._num(y))
        self.ops.append("BT /F1 1 Tf %s (%s) Tj ET" % (tm, s))

    def save(self, path):
        content = ("q\n%s 0 0 %s 0 0 cm\n1 J 1 j 0 G 0 g\n" % (
            self._num(MM), self._num(MM))) + "\n".join(self.ops) + "\nQ\n"
        stream = content.encode("latin-1")
        objs = [
            b"<< /Type /Catalog /Pages 2 0 R >>",
            b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            ("<< /Type /Page /Parent 2 0 R /MediaBox [0 0 %s %s] "
             "/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>" % (
                 self._num(self.w * MM), self._num(self.h * MM))).encode("ascii"),
            b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"endstream",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica "
            b"/Encoding /WinAnsiEncoding >>",
        ]
        out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offsets = []
        for i, body in enumerate(objs, 1):
            offsets.append(len(out))
            out += b"%d 0 obj\n" % i + body + b"\nendobj\n"
        xref = len(out)
        out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
        for off in offsets:
            out += b"%010d 00000 n \n" % off
        out += (b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n"
                % (len(objs) + 1, xref))
        with open(path, "wb") as f:
            f.write(bytes(out))


def dim_h(s, x1, x2, y, label, w=0.15):
    """Horizontal dimension line with end ticks and a centred label."""
    s.line(x1, y, x2, y, w)
    for x in (x1, x2):
        s.line(x, y - 1.2, x, y + 1.2, w)
    s.text(label, (x1 + x2) / 2.0 - len(label) * 0.75, y + 1.6, 2.6)


def dim_v(s, x, y1, y2, label, w=0.15):
    """Vertical dimension line with end ticks and a rotated label."""
    s.line(x, y1, x, y2, w)
    for y in (y1, y2):
        s.line(x - 1.2, y, x + 1.2, y, w)
    s.text(label, x - 1.0, (y1 + y2) / 2.0 - len(label) * 0.75, 2.6, angle=90)


def b2p(x, y):
    """Board coordinates (y down) to page coordinates (y up)."""
    return BX + x, BY + (BOARD_H - y)


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_OUT
    sheet = Sheet(A4_W, A4_H)
    s = sheet

    s.text("KVM-BOARD  /  FRISK case fit check", BX, 190, 6.0)
    s.text("Actual size (1:1). Print at 100% - do not use 'fit to page'.", BX, 183, 3.4)
    s.text("If the 100 mm scale at the bottom does not measure 100 mm, the print is scaled.",
           BX, 178.5, 3.0)

    # --- case inner tray (board + 0.5 mm on every side) -----------------
    s.rect(BX - CASE_CLEARANCE, BY - CASE_CLEARANCE,
           BOARD_W + 2 * CASE_CLEARANCE, BOARD_H + 2 * CASE_CLEARANCE,
           0.25, dash=(2.0, 1.2))

    # --- board outline --------------------------------------------------
    for (x1, y1), (x2, y2) in read_outline(PCB):
        p1, p2 = b2p(x1, y1), b2p(x2, y2)
        s.line(p1[0], p1[1], p2[0], p2[1], 0.35)

    # --- connector bodies and mouths ------------------------------------
    for ref, cx, cy, rot in (("J1", J1_X, J1_Y, 270), ("J2", J2_X, J2_Y, 90)):
        if rot in (90, 270):
            hx, hy = SHELL_Y / 2.0, SHELL_X / 2.0
        else:
            hx, hy = SHELL_X / 2.0, SHELL_Y / 2.0
        x0, y0 = b2p(cx - hx, cy + hy)
        s.rect(x0, y0, 2 * hx, 2 * hy, 0.15, dash=(1.0, 1.0))
        s.text(ref, x0 + 1.0, y0 + 1.4, 2.6)

    # --- main silkscreen text at 1:1 -------------------------------------
    for text, x, y, size in read_silk_text(PCB):
        if size < 0.85:
            continue
        px, py = b2p(x, y)
        s.text(text, px - len(text) * size * 0.29, py - size * 0.35, size)

    # --- connector centre lines -----------------------------------------
    for yb in (J1_Y, J2_Y):
        _, py = b2p(0, yb)
        s.line(BX - 6, py, BX + BOARD_W + 19, py, 0.12, dash=(1.5, 1.5))

    # --- dimensions ------------------------------------------------------
    dim_h(s, BX, BX + BOARD_W, BY - 9, "65.4")
    dim_v(s, BX - 8, BY, BY + BOARD_H, "31.4")
    dim_v(s, BX + BOARD_W + 4, BY, BY + 19.8, "19.8")
    dim_v(s, BX + BOARD_W + 11, BY + BOARD_H - J1_Y, BY + BOARD_H, "14.0")
    dim_v(s, BX + BOARD_W + 18, BY + BOARD_H - J2_Y, BY + BOARD_H, "5.5")

    # --- legend ----------------------------------------------------------
    ly = 92.0
    s.line(BX, ly, BX + 12, ly, 0.35)
    s.text("board outline (solid, 1:1)", BX + 15, ly - 1.0, 2.8)
    s.line(BX, ly - 6, BX + 12, ly - 6, 0.25, dash=(2.0, 1.2))
    s.text("case tray 66.4 x 32.4 (dashed)", BX + 15, ly - 7.0, 2.8)
    s.line(BX, ly - 12, BX + 12, ly - 12, 0.12, dash=(1.5, 1.5))
    s.text("connector centre line", BX + 15, ly - 13.0, 2.8)

    # --- notes -----------------------------------------------------------
    nx, ny = 132.0, 172.0
    s.text("HOW TO CHECK", nx, ny, 4.0)
    lines = [
        "1. Print this page at 100% / 'Actual size'.",
        "2. Measure the 100 mm scale below with a steel rule.",
        "3. Cut out the solid outline and drop it into the tray.",
        "4. The dashed line is the tray: 66.4 x 32.4 mm; the",
        "   board is 0.5 mm smaller on every side.",
        "5. The notch (6.8 x 19.8 mm) must clear the latch",
        "   island in the lower-right corner of the tray.",
        "6. J1 (left) and J2 (right) mouths must sit on the case",
        "   walls; cut about 10 x 4 mm openings there,",
        "   1.4 to 5.1 mm above the tray floor.",
        "7. There are no mounting holes: use tape or foam, with",
        "   about 1 mm spacer under the board.",
    ]
    for i, line in enumerate(lines):
        s.text(line, nx, ny - 6.5 - i * 4.6, 2.9)

    s.text("DIMENSIONS (mm)", nx, 105.0, 3.4)
    for i, line in enumerate([
        "board          65.4 x 31.4 x 1.6",
        "case tray      66.4 x 32.4",
        "case outer     69 x 37, tray depth 9.8",
        "J1 centre      14.0 from the top edge",
        "J2 centre      5.5 from the top edge",
        "notch          6.8 x 19.8, lower-right",
    ]):
        s.text(line, nx, 99.0 - i * 5.2, 2.9)

    # --- 100 mm scale check ---------------------------------------------
    sx, sy, slen = BX, 66.0, 100.0
    s.line(sx, sy, sx + slen, sy, 0.3)
    for i in range(int(slen) + 1):
        if i % 10 == 0:
            tick, w = 3.2, 0.3
        elif i % 5 == 0:
            tick, w = 2.0, 0.2
        else:
            tick, w = 1.0, 0.15
        s.line(sx + i, sy, sx + i, sy + tick, w)
    for i in range(0, int(slen) + 1, 50):
        s.text("%d" % i, sx + i - (3 if i == 100 else 0), sy - 4.5, 3.0)
    s.text("100 mm scale check (mm)", sx, sy + 7.0, 3.2)

    s.text("Generated by scripts/gen_print_sheet.py from kvm-board.kicad_pcb",
           BX, 35.0, 2.4)

    os.makedirs(os.path.dirname(out), exist_ok=True)
    sheet.save(out)
    print("wrote %s (A4 landscape, 1:1)" % os.path.relpath(out, ROOT))


if __name__ == "__main__":
    main()
