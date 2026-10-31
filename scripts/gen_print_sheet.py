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
BOARD_W, BOARD_H = 57.6, 31.4
CASE_CLEARANCE = 0.5
CASE_W, CASE_H = 67.0, 32.4
LATCH_DEPTH = 8.4

# Connector centres in board coordinates (y from the top edge).  Both are on
# the left edge, stacked around the board centre line.
J1_Y, J2_Y = 9.7, 21.7
J1_X = J2_X = 2.129
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


def outline_polygon(segs, tol=1e-3):
    """Chain Edge.Cuts segments into one closed polygon."""
    remaining = list(segs)
    start, end = remaining.pop(0)
    pts = [start, end]
    while remaining:
        last = pts[-1]
        for i, (a, b) in enumerate(remaining):
            if abs(last[0] - a[0]) < tol and abs(last[1] - a[1]) < tol:
                pts.append(b)
                remaining.pop(i)
                break
            if abs(last[0] - b[0]) < tol and abs(last[1] - b[1]) < tol:
                pts.append(a)
                remaining.pop(i)
                break
        else:
            raise SystemExit("Edge.Cuts is not a single closed loop")
    if abs(pts[0][0] - pts[-1][0]) < tol and abs(pts[0][1] - pts[-1][1]) < tol:
        pts.pop()
    return pts


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

    def _path(self, pts):
        out = ["%s %s m" % (self._num(pts[0][0]), self._num(pts[0][1]))]
        for x, y in pts[1:]:
            out.append("%s %s l" % (self._num(x), self._num(y)))
        out.append("h")
        return " ".join(out)

    def fill(self, pts, gray=0.7):
        self.ops.append("%s g %s f 0 g" % (self._num(gray), self._path(pts)))

    def stroke_polygon(self, pts, width=1.0, gray=0.85):
        self.ops.append("%s G %s w %s S 0 G" % (
            self._num(gray), self._num(width), self._path(pts)))

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

    # --- case inner tray and latch island (reference only) --------------
    cx0, cy0 = BX - CASE_CLEARANCE, BY - CASE_CLEARANCE
    s.rect(cx0, cy0, CASE_W, CASE_H, 0.12, dash=(2.0, 1.2))
    island_x = cx0 + CASE_W - LATCH_DEPTH
    island_h = CASE_H - 11.0
    s.fill([(island_x, cy0), (cx0 + CASE_W, cy0),
            (cx0 + CASE_W, cy0 + island_h), (island_x, cy0 + island_h)], 0.90)
    s.rect(island_x, cy0, LATCH_DEPTH, island_h, 0.12, dash=(1.5, 1.0))
    s.text("latch", island_x + 2.2, cy0 + 4.0, 2.4, angle=90)

    # --- board outline and 0.5 mm case-clearance band -------------------
    poly = outline_polygon(read_outline(PCB))
    pts = [b2p(x, y) for x, y in poly]
    # A 1.0 mm wide stroke centred on the edge leaves a 0.5 mm light-grey
    # band outside the board once the board itself is filled on top.
    s.stroke_polygon(pts, width=2 * CASE_CLEARANCE, gray=0.87)
    s.fill(pts, gray=0.68)
    s.stroke_polygon(pts, width=0.15, gray=0.25)

    # --- connector bodies and mouths ------------------------------------
    for ref, cx, cy, rot in (("J1", J1_X, J1_Y, 270),
                             ("J2", J2_X, J2_Y, 270)):
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
    dim_h(s, BX, BX + BOARD_W, BY - 9, "57.6")
    dim_h(s, cx0, cx0 + CASE_W, BY - 15, "67.0 case inner")
    dim_v(s, BX - 8, BY, BY + BOARD_H, "31.4")
    dim_v(s, BX + BOARD_W + 11, BY + BOARD_H - J1_Y, BY + BOARD_H, "9.7")
    dim_v(s, BX + BOARD_W + 18, BY + BOARD_H - J2_Y, BY + BOARD_H, "21.7")

    # --- legend ----------------------------------------------------------
    ly = 92.0
    s.fill([(BX, ly), (BX + 12, ly), (BX + 12, ly + 3.2), (BX, ly + 3.2)], 0.68)
    s.stroke_polygon([(BX, ly), (BX + 12, ly), (BX + 12, ly + 3.2),
                      (BX, ly + 3.2)], 0.15, 0.25)
    s.text("board (solid grey, 1:1)", BX + 15, ly - 0.4, 2.8)
    s.fill([(BX, ly - 6), (BX + 12, ly - 6), (BX + 12, ly - 2.8),
            (BX, ly - 2.8)], 0.87)
    s.text("0.5 mm case clearance (light grey)", BX + 15, ly - 5.6, 2.8)
    s.line(BX, ly - 12, BX + 12, ly - 12, 0.12, dash=(1.5, 1.5))
    s.text("connector centre line", BX + 15, ly - 13.0, 2.8)
    s.fill([(BX, ly - 18), (BX + 12, ly - 18), (BX + 12, ly - 14.8),
            (BX, ly - 14.8)], 0.90)
    s.text("case latch island (do not cover)", BX + 15, ly - 17.6, 2.8)

    # --- notes -----------------------------------------------------------
    nx, ny = 132.0, 172.0
    s.text("HOW TO CHECK", nx, ny, 4.0)
    lines = [
        "1. Print this page at 100% / 'Actual size'.",
        "2. Measure the 100 mm scale below with a steel rule.",
        "3. Cut out the solid grey board and drop it into the tray.",
        "4. Board 57.6 x 31.4, case inner 67.0 x 32.4. The light",
        "   grey band is the 0.5 mm clearance to the left, top and",
        "   bottom walls.",
        "5. The right edge is one straight cut, 0.5 mm from the",
        "   latch island. The right 8.9 mm of the tray stays empty.",
        "6. Both Type-C mouths are on the left edge at 9.7 and",
        "   21.7 mm from the top (6.0 mm either side of centre).",
        "   Each mouth overhangs the edge by 1.5 mm.",
        "7. Cut two 10 x 4 mm openings through the left wall,",
        "   centred on the two dashed centre lines. Chamfer the",
        "   outside by about 0.3 mm.",
        "8. There are no mounting holes: use tape or foam, with",
        "   about 1 mm spacer under the board.",
    ]
    for i, line in enumerate(lines):
        s.text(line, nx, ny - 6.5 - i * 3.7, 2.9)

    s.text("DIMENSIONS (mm)", nx, 100.0, 3.4)
    for i, line in enumerate([
        "board          57.6 x 31.4 x 1.6",
        "case           67.0 x 32.4 inner, 1.0 wall",
        "left/top/bottom gap 0.5",
        "right edge     0.5 from the latch island",
        "J1 / J2 centre 9.7 / 21.7 from the top",
        "connector pitch 12.0 (6.0 each side of centre)",
        "mouth          1.5 past the left edge",
    ]):
        s.text(line, nx, 94.0 - i * 5.2, 2.9)

    # --- 100 mm scale check ---------------------------------------------
    sx, sy, slen = BX, 52.0, 100.0
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
