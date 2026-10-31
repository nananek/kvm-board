"""Generate the kvm-board PCB with pcbnew (KiCad 10 python API).

Layout summary
--------------
Board 57.6 x 31.4 mm.  It is the 67.0 mm FRISK tray width minus the 0.5 mm
left gap, the 0.5 mm gap to the latch island, and the 8.4 mm island depth,
so the right edge is one straight cut.
J1 = serial (CH340N) and J2 = HID (CH9329) both sit on the left short edge,
stacked around the vertical centre.  Their mouths overhang the edge by
1.5 mm, through two openings cut in the case wall.
Both connectors are sinks (5.1k CC pulldowns).
+5V is diode-OR'ed from both VBUS pins and distributed on the top layer.
GND is a copper pour on both layers.
"""

import math
import os
import sys

import pcbnew

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from design import PROJECT, PARTS, GND, P5V  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FP_DIR = os.path.join(ROOT, "lib", "KVM.pretty")

W, H = 57.6, 31.4
# The old latch notch started 8.4 mm in from the 66.0 mm outline.  Cutting
# the whole right side back to that line removes the lobe and the notch while
# keeping the 0.5 mm clearance to the case's latch island.
THICKNESS = 1.6

# reference -> (footprint name, x, y, rotation)
# Both Type-C receptacles are on the left edge, mouths facing left.  Their
# shells span y = 5.23..14.17 (J1) and 17.23..26.17 (J2), so the pair is
# centred on the board's y = 15.7 mm centre line with a 3.06 mm gap.
PLACE = {
    "J1": ("USB_C_Receptacle_HRO_TYPE-C-31-M-12", 2.129, 9.7, 270),
    "J2": ("USB_C_Receptacle_HRO_TYPE-C-31-M-12", 2.129, 21.7, 270),
    "U2": ("SO-8_3.9x4.9mm_P1.27mm", 19.5, 14.0, 0),
    "U1": ("SO-16_3.9x9.9mm_P1.27mm", 36.5, 14.0, 0),
    "D1": ("D_SOD-323", 11.0, 6.0, 180),
    "D2": ("D_SOD-323", 20.0, 27.0, 180),
    "D3": ("SOT-23-6", 13.0, 13.5, 0),
    "D4": ("SOT-23-6", 22.0, 22.0, 180),
    "R1": ("R_0603_1608Metric", 10.0, 2.0, 0),
    "R2": ("R_0603_1608Metric", 9.0, 15.0, 0),
    "R3": ("R_0603_1608Metric", 9.0, 17.5, 0),
    "R4": ("R_0603_1608Metric", 10.0, 24.5, 0),
    "R5": ("R_0603_1608Metric", 31.0, 4.0, 0),
    "LED1": ("LED_0603_1608Metric", 35.0, 4.0, 180),
    "C1": ("C_0603_1608Metric", 43.675, 9.0, 180),
    "C2": ("C_0603_1608Metric", 15.5, 17.5, 180),
    "C3": ("C_0603_1608Metric", 25.2, 11.5, 0),
    "C4": ("C_0603_1608Metric", 41.5, 7.0, 0),
    "C5": ("C_0805_2012Metric", 29.0, 8.0, 0),
    "C6": ("C_0603_1608Metric", 12.0, 16.2, 0),
    "C7": ("C_0603_1608Metric", 24.0, 27.0, 0),
    "TP1": ("TestPoint_1P", 44.0, 17.0, 0),
    "TP2": ("TestPoint_1P", 46.54, 17.0, 0),
}

SIG_W = 0.2
PWR_W = 0.3
VIA_D = 0.5
VIA_DRILL = 0.3


def P(x, y):
    return pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y))


def board_points(inset=0.0, steps=16):
    """Return the board outline as a closed polygon.

    The left corners are rounded to match the case; the right edge is one
    straight cut, because the latch-island lobe and notch are gone.  ``inset``
    shrinks every edge for the GND zone.
    """
    left = inset
    right = W - inset
    top = inset
    bottom = H - inset
    r_out = max(0.1, 2.0 - inset)

    def arc(cx, cy, r, a0, a1):
        out = []
        for i in range(steps + 1):
            a = math.radians(a0 + (a1 - a0) * i / steps)
            out.append((cx + r * math.cos(a), cy + r * math.sin(a)))
        return out

    pts = [(right, top)]
    pts.append((right, bottom))
    pts += arc(left + r_out, bottom - r_out, r_out, 90, 180)
    pts.append((left, top + r_out))
    pts += arc(left + r_out, top + r_out, r_out, 180, 270)
    # Remove consecutive duplicates (arc endpoints shared with the next edge).
    clean = []
    for p in pts:
        if not clean or abs(p[0] - clean[-1][0]) > 1e-6 or abs(p[1] - clean[-1][1]) > 1e-6:
            clean.append(p)
    if len(clean) > 1 and abs(clean[0][0] - clean[-1][0]) < 1e-6 and abs(clean[0][1] - clean[-1][1]) < 1e-6:
        clean.pop()
    return clean



class Builder:
    def __init__(self):
        self.board = pcbnew.BOARD()
        self.board.GetDesignSettings().SetBoardThickness(pcbnew.FromMM(THICKNESS))
        self.board.GetDesignSettings().m_CopperEdgeClearance = pcbnew.FromMM(0.2)
        # drill/place origin at the bottom-left corner, so the gerbers and the
        # JLCPCB CPL share the same coordinate system
        self.board.GetDesignSettings().SetAuxOrigin(P(0, H))
        self.nets = {}
        self.pads = {}
        self._add_nets()
        self._place()

    # -- setup ---------------------------------------------------------
    def _add_nets(self):
        names = sorted({n for p in PARTS for n in p["pins"].values() if n})
        for name in names:
            ni = pcbnew.NETINFO_ITEM(self.board, name)
            self.board.Add(ni)
            self.nets[name] = ni
        self.nets[GND] = self.board.FindNet(GND)
        self.nets[P5V] = self.board.FindNet(P5V)

    def _place(self):
        for part in PARTS:
            fpname, x, y, rot = PLACE[part["ref"]]
            fp = pcbnew.FootprintLoad(FP_DIR, fpname)
            if fp is None:
                raise RuntimeError("footprint not found: " + fpname)
            fp.SetPosition(P(x, y))
            fp.SetOrientationDegrees(rot)
            self.board.Add(fp)
            fp.SetReference(part["ref"])
            fp.SetValue(part["value"])
            if part["ref"] not in ("U1", "U2"):
                fp.Reference().SetVisible(False)
                fp.Value().SetVisible(False)
            if part["ref"] in ("J1", "J2"):
                for g in fp.GraphicalItems():
                    if g.GetLayer() == pcbnew.F_SilkS:
                        bb = g.GetBoundingBox()
                        x0 = pcbnew.ToMM(bb.GetX())
                        x1 = x0 + pcbnew.ToMM(bb.GetWidth())
                        if x0 < 1.0 or x1 > W - 1.0:
                            g.SetLayer(pcbnew.F_Fab)
            for pad in fp.Pads():
                num = pad.GetNumber()
                pad.SetLocalSolderMaskMargin(0)
                net = part["pins"].get(num)
                if net:
                    pad.SetNet(self.nets[net])
                if net == GND:
                    pad.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_FULL)
                self.pads[(part["ref"], num)] = pad

    # -- geometry helpers ---------------------------------------------
    def pad(self, ref, num):
        p = self.pads[(ref, num)].GetPosition()
        return (pcbnew.ToMM(p.x), pcbnew.ToMM(p.y))

    def track(self, net, pts, layer=pcbnew.F_Cu, width=SIG_W):
        for a, b in zip(pts, pts[1:]):
            t = pcbnew.PCB_TRACK(self.board)
            t.SetStart(P(*a))
            t.SetEnd(P(*b))
            t.SetWidth(pcbnew.FromMM(width))
            t.SetLayer(layer)
            t.SetNet(self.nets[net])
            self.board.Add(t)

    def via(self, net, x, y, size=VIA_D, drill=VIA_DRILL):
        v = pcbnew.PCB_VIA(self.board)
        v.SetPosition(P(x, y))
        v.SetWidth(pcbnew.FromMM(size))
        v.SetDrill(pcbnew.FromMM(drill))
        try:
            v.SetViaType(pcbnew.VIATYPE_THROUGH)
        except AttributeError:
            # KiCad 9 removed the VIATYPE_* constants; a new PCB_VIA is through.
            pass
        v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
        v.SetNet(self.nets[net])
        self.board.Add(v)

    # -- construction --------------------------------------------------
    def outline(self):
        pts = board_points()
        for a, b in zip(pts, pts[1:] + pts[:1]):
            if abs(a[0] - b[0]) < 1e-9 and abs(a[1] - b[1]) < 1e-9:
                continue
            seg = pcbnew.PCB_SHAPE(self.board)
            seg.SetShape(pcbnew.SHAPE_T_SEGMENT)
            seg.SetLayer(pcbnew.Edge_Cuts)
            seg.SetStart(P(*a))
            seg.SetEnd(P(*b))
            seg.SetWidth(pcbnew.FromMM(0.1))
            self.board.Add(seg)

    def zones(self):
        outline = board_points(0.3)
        for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
            z = pcbnew.ZONE(self.board)
            z.SetLayer(layer)
            z.SetNet(self.nets[GND])
            z.SetLocalClearance(pcbnew.FromMM(0.2))
            z.SetMinThickness(pcbnew.FromMM(0.2))
            z.SetThermalReliefGap(pcbnew.FromMM(0.25))
            z.SetThermalReliefSpokeWidth(pcbnew.FromMM(0.3))
            z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
            o = z.Outline()
            o.NewOutline()
            for x, y in outline:
                o.Append(P(x, y))
            self.board.Add(z)

    def texts(self):
        def text(s, x, y, size=1.0, w=0.15, layer=pcbnew.F_SilkS):
            t = pcbnew.PCB_TEXT(self.board)
            t.SetText(s)
            t.SetPosition(P(x, y))
            t.SetLayer(layer)
            t.SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(size), pcbnew.FromMM(size)))
            t.SetTextThickness(pcbnew.FromMM(w))
            t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_CENTER)
            self.board.Add(t)

        text("SERIAL / CH340", 15.5, 19.5, 0.9)
        text("HID / CH9329", 14.0, 30.0, 1.0)
        text("KVM-BOARD  CH9329EMU-USB replacement", 28.8, 2.4, 0.9, 0.13)
        # pin-1 / polarity marks for datasheet comparison
        text("1", 32.2, 8.2, 0.8)
        text("1", 14.0, 10.6, 0.8)
        text("1", 10.0, 11.0, 0.8)
        text("K", 12.05, 4.6, 0.8)
        text("K", 21.05, 25.6, 0.8)
        text("K", 37.0, 5.2, 0.8)
        # A1 marks: both connectors are rotated 270 deg, so A1 is at the top
        # of each shell.  J2's mark sits between the two connectors.
        text("A1", 3.5, 4.0, 0.8)
        text("A1", 8.0, 16.5, 0.8)
        text("U1 CH9329   U2 CH340N", 40.0, 24.2, 0.8, 0.1)
        text("D1,D2 BAT54WS   D3,D4 USBLC6-2SC6", 40.0, 25.3, 0.8, 0.1)
        # SET / GND test pads to the right of U1 (TP1 / TP2)
        text("SET", 44.0, 15.35, 0.8, 0.1)
        text("GND", 46.54, 15.35, 0.8, 0.1)
        text("SHORT TO CONFIGURE", 45.0, 20.5, 0.8, 0.1)

    def qr_code(self):
        """Draw the repository QR code on the bottom silkscreen.

        The text file holds the QR as seen from the bottom (1 = dark module).
        Board coordinates are mirrored horizontally so the code reads the right
        way round when the finished board is turned over.
        """
        path = os.path.join(ROOT, "scripts", "repo_qr.txt")
        rows = []
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                rows.append(line)
        n = len(rows)
        if n == 0 or any(len(row) != n for row in rows):
            raise RuntimeError("repo_qr.txt is not a square matrix")

        cell = 0.5
        x0 = 20.5
        y0 = 11.75
        for r, row in enumerate(rows):
            c = 0
            while c < n:
                if row[c] != "0":
                    c += 1
                    continue
                c_end = c
                while c_end < n and row[c_end] == "0":
                    c_end += 1
                # mirror the run: bottom-view column c maps to board column n-1-c
                xa = x0 + (n - c_end) * cell
                xb = x0 + (n - c) * cell
                ya = y0 + r * cell
                yb = y0 + (r + 1) * cell
                rect = pcbnew.PCB_SHAPE(self.board)
                rect.SetShape(pcbnew.SHAPE_T_RECT)
                rect.SetStart(P(xa, ya))
                rect.SetEnd(P(xb, yb))
                rect.SetLayer(pcbnew.B_SilkS)
                rect.SetWidth(pcbnew.FromMM(0.05))
                rect.SetFilled(True)
                self.board.Add(rect)
                c = c_end

    # -- routing -------------------------------------------------------
    def route(self):
        T = self.track
        V = self.via

        # ---------------- +5V (diode OR of both VBUS) ----------------
        # The rail runs along the top edge; D2 at the bottom feeds it through
        # a B.Cu return along the lower edge.
        T(P5V, [(12.05, 6.0), (48.2, 6.0)], width=PWR_W)

        # serial VBUS: both J1 VBUS pads -> B.Cu trunk -> D1, C6, D3
        T("VBUS_SER", [self.pad("J1", "A4"), (7.5, 7.25)], width=SIG_W)
        V("VBUS_SER", 7.5, 7.25)
        T("VBUS_SER", [self.pad("J1", "A9"), (7.5, 12.15)], width=SIG_W)
        V("VBUS_SER", 7.5, 12.15)
        T("VBUS_SER", [(7.5, 7.25), (7.5, 16.2)],
          layer=pcbnew.B_Cu, width=PWR_W)
        T("VBUS_SER", [(7.5, 7.25), (7.5, 6.0), (8.8, 6.0)],
          layer=pcbnew.B_Cu, width=PWR_W)
        V("VBUS_SER", 8.8, 6.0)
        T("VBUS_SER", [(8.8, 6.0), self.pad("D1", "2")], width=PWR_W)
        T("VBUS_SER", [(7.5, 16.2), (10.7, 16.2)],
          layer=pcbnew.B_Cu, width=SIG_W)
        V("VBUS_SER", 10.7, 16.2)
        T("VBUS_SER", [(10.7, 16.2), self.pad("C6", "1")], width=SIG_W)
        T("VBUS_SER", [(10.7, 16.2), (15.0, 16.2), (15.0, 13.5)],
          layer=pcbnew.B_Cu, width=SIG_W)
        V("VBUS_SER", 15.0, 13.5)
        T("VBUS_SER", [(15.0, 13.5), self.pad("D3", "5")], width=SIG_W)

        # HID VBUS: both J2 VBUS pads -> B.Cu trunk down the left -> D2 / C7
        T("VBUS_HID", [self.pad("J2", "A4"), (7.2, 19.25)], width=PWR_W)
        V("VBUS_HID", 7.2, 19.25)
        T("VBUS_HID", [self.pad("J2", "A9"), (7.2, 24.15)], width=PWR_W)
        V("VBUS_HID", 7.2, 24.15)
        T("VBUS_HID", [(7.2, 19.25), (7.2, 28.0)],
          layer=pcbnew.B_Cu, width=PWR_W)
        V("VBUS_HID", 7.2, 28.0)
        T("VBUS_HID", [(7.2, 28.0), (23.225, 28.0)], width=SIG_W)
        T("VBUS_HID", [(18.95, 28.0), (18.95, 27.0)], width=SIG_W)
        T("VBUS_HID", [(23.225, 28.0), (23.225, 27.0)], width=SIG_W)
        # D4 pin 5 (VBUS) sits in the middle of the left pad row; leave the
        # pin 4/6 rows alone and drop down on the left of the package.
        T("VBUS_HID", [self.pad("D4", "5"), (18.95, 22.0),
                       (18.95, 24.5)], width=SIG_W)
        V("VBUS_HID", 18.95, 24.5)
        T("VBUS_HID", [(18.95, 24.5), (18.95, 28.0)],
          layer=pcbnew.B_Cu, width=SIG_W)
        V("VBUS_HID", 18.95, 28.0)

        # D2 cathode -> +5V.  Cross the lower-edge signals on B.Cu.
        T(P5V, [self.pad("D2", "1"), (22.0, 27.0), (22.0, 26.0),
                (22.6, 26.0)], width=PWR_W)
        V(P5V, 22.6, 26.0)
        T(P5V, [(22.6, 26.0), (22.6, 30.0), (48.2, 30.0)],
          layer=pcbnew.B_Cu, width=PWR_W)
        V(P5V, 48.2, 30.0)
        T(P5V, [(48.2, 30.0), (48.2, 6.0)], width=PWR_W)

        # U2 (CH340N) VCC: drop under the data signals on the back layer
        V(P5V, 20.0, 6.0)
        T(P5V, [(20.0, 6.0), (20.0, 18.5)], layer=pcbnew.B_Cu, width=PWR_W)
        V(P5V, 20.0, 18.5)
        T(P5V, [(20.0, 18.5), (22.075, 18.5), (22.075, 15.905)], width=PWR_W)
        T(P5V, [self.pad("C2", "1"), (16.275, 18.5), (20.0, 18.5)], width=SIG_W)
        # U1 (CH9329) VCC
        T(P5V, [(44.5, 6.0), (44.5, 10.825)], width=PWR_W)
        T(P5V, [(44.5, 10.825), self.pad("U1", "15")], width=PWR_W)
        # decoupling caps + LED
        T(P5V, [(self.pad("C5", "1")[0], 6.0), self.pad("C5", "1")], width=SIG_W)
        T(P5V, [self.pad("R5", "1"), (30.175, 6.0)], width=SIG_W)

        # ---------------- serial port USB ----------------
        T("USB_SER_DP", [self.pad("J1", "A6"), (8.9, 9.45)], width=SIG_W)
        T("USB_SER_DP", [self.pad("J1", "B6"), (8.9, 10.45)], width=SIG_W)
        T("USB_SER_DP", [(8.9, 9.45), (8.9, 10.45)], width=SIG_W)
        T("USB_SER_DP", [(8.9, 10.45), (9.2, 10.45), (9.2, 12.55),
                         self.pad("D3", "1")], width=SIG_W)
        T("USB_SER_DP", [self.pad("D3", "1"), self.pad("D3", "6")], width=SIG_W)
        T("USB_SER_DP", [self.pad("D3", "6"), (15.0, 12.55), (15.0, 12.095),
                         self.pad("U2", "1")], width=SIG_W)
        T("USB_SER_DM", [self.pad("J1", "B7"), (8.4, 8.95)], width=SIG_W)
        V("USB_SER_DM", 8.4, 8.95, size=0.35, drill=0.15)
        T("USB_SER_DM", [self.pad("J1", "A7"), (8.4, 9.95)], width=SIG_W)
        V("USB_SER_DM", 8.4, 9.95, size=0.35, drill=0.15)
        T("USB_SER_DM", [(8.4, 8.95), (8.4, 9.95)],
          layer=pcbnew.B_Cu, width=SIG_W)
        T("USB_SER_DM", [(8.4, 9.95), (9.3, 9.95), (9.3, 14.45),
                         (10.5, 14.45)], layer=pcbnew.B_Cu, width=SIG_W)
        V("USB_SER_DM", 10.5, 14.45, size=0.35, drill=0.15)
        T("USB_SER_DM", [(10.5, 14.45), self.pad("D3", "3")], width=SIG_W)
        T("USB_SER_DM", [self.pad("D3", "3"), self.pad("D3", "4")], width=SIG_W)
        T("USB_SER_DM", [self.pad("D3", "4"), (15.6, 14.45), (15.6, 13.365),
                         self.pad("U2", "2")], width=SIG_W)

        # ---------------- HID port USB ----------------
        # D+ stays on F.Cu all the way to D4 pin 4.  D- drops to B.Cu at the
        # pads; keeping the two nets on different layers avoids the pad order
        # crossing (B7, A6, A7, B6).
        T("USB_HID_DP", [self.pad("J2", "A6"), (8.9, 21.45)], width=SIG_W)
        T("USB_HID_DP", [self.pad("J2", "B6"), (8.9, 22.45)], width=SIG_W)
        T("USB_HID_DP", [(8.9, 21.45), (8.9, 22.45)], width=SIG_W)
        T("USB_HID_DP", [(8.9, 21.45), (9.5, 21.45), (9.5, 21.05),
                         self.pad("D4", "4")], width=SIG_W)
        T("USB_HID_DP", [self.pad("D4", "3"), self.pad("D4", "4")],
          width=SIG_W)

        T("USB_HID_DM", [self.pad("J2", "B7"), (7.8, 20.95)], width=SIG_W)
        V("USB_HID_DM", 7.8, 20.95, size=0.35, drill=0.15)
        T("USB_HID_DM", [self.pad("J2", "A7"), (7.8, 21.95)], width=SIG_W)
        V("USB_HID_DM", 7.8, 21.95, size=0.35, drill=0.15)
        T("USB_HID_DM", [(7.8, 20.95), (7.8, 21.95)],
          layer=pcbnew.B_Cu, width=SIG_W)
        T("USB_HID_DM", [(7.8, 21.95), (18.8, 21.95), (18.8, 22.95),
                         (19.8, 22.95)], layer=pcbnew.B_Cu, width=SIG_W)
        V("USB_HID_DM", 19.8, 22.95, size=0.35, drill=0.15)
        T("USB_HID_DM", [(19.8, 22.95), self.pad("D4", "6")], width=SIG_W)
        T("USB_HID_DM", [self.pad("D4", "1"), self.pad("D4", "6")],
          width=SIG_W)

        # CC pulldowns: stay on F.Cu above/below the data traces.
        T("CC1_HID", [self.pad("J2", "A5"), (8.6, 20.45), (8.6, 17.5),
                      (8.175, 17.5)], width=SIG_W)
        T("CC2_HID", [self.pad("J2", "B5"), (8.0, 23.45), (8.0, 24.5),
                      (9.175, 24.5)], width=SIG_W)

        # D4 -> U1.  DM is I/O1 (pins 1/6), DP is I/O2 (pins 3/4).  The two
        # runs use B.Cu to the right of U1, then short F.Cu stubs to the pins.
        # DM turns up farther right so it does not cross the DP run.
        T("USB_HID_DM", [self.pad("D4", "1"), (24.5, 22.95)], width=SIG_W)
        V("USB_HID_DM", 24.5, 22.95, size=0.35, drill=0.15)
        T("USB_HID_DM", [(24.5, 22.95), (41.8, 22.95), (41.8, 14.2)],
          layer=pcbnew.B_Cu, width=SIG_W)
        V("USB_HID_DM", 41.8, 14.2, size=0.35, drill=0.15)
        T("USB_HID_DM", [(41.8, 14.2), (41.8, 13.365),
                         self.pad("U1", "13")], width=SIG_W)

        T("USB_HID_DP", [self.pad("D4", "3"), (24.5, 21.05)], width=SIG_W)
        V("USB_HID_DP", 24.5, 21.05, size=0.35, drill=0.15)
        T("USB_HID_DP", [(24.5, 21.05), (41.2, 21.05), (41.2, 15.2)],
          layer=pcbnew.B_Cu, width=SIG_W)
        V("USB_HID_DP", 41.2, 15.2, size=0.35, drill=0.15)
        T("USB_HID_DP", [(41.2, 15.2), (41.2, 14.635),
                         self.pad("U1", "12")], width=SIG_W)

        # ---------------- CC pulldowns (serial side) ----------------
        T("CC1_SER", [self.pad("J1", "A5"), (8.3, 8.45), (8.3, 2.0),
                      self.pad("R1", "1")], width=SIG_W)
        T("CC2_SER", [self.pad("J1", "B5"), (8.6, 11.45), (8.6, 15.0),
                      (8.175, 15.0)], width=SIG_W)

        # ---------------- UART between CH340N and CH9329 ----------------
        T("UART_9329_TX", [self.pad("U2", "6"), (23.5, 14.635), (23.5, 17.8),
                           (32.0, 17.8), (32.0, 18.445), self.pad("U1", "8")],
          width=SIG_W)
        T("UART_9329_RX", [self.pad("U1", "7"), (31.0, 17.175), (31.0, 13.365),
                           self.pad("U2", "7")], width=SIG_W)

        # ---------------- LED (cathode crosses the +5V rail on B.Cu) --------
        T("LED_A", [self.pad("R5", "2"), self.pad("LED1", "2")], width=SIG_W)
        led_x = self.pad("LED1", "1")[0]
        T("LED_ACT", [self.pad("LED1", "1"), (led_x, 5.0)], width=SIG_W)
        V("LED_ACT", led_x, 5.0)
        T("LED_ACT", [(led_x, 5.0), (led_x, 8.0)], layer=pcbnew.B_Cu, width=SIG_W)
        V("LED_ACT", led_x, 8.0)
        T("LED_ACT", [(led_x, 8.0), (33.425, 8.0), (33.425, 9.555),
                      self.pad("U1", "1")], width=SIG_W)

        # ---------------- V33 / V3 ----------------
        T("V33", [self.pad("C4", "1"), (40.3, 7.0), (40.3, 9.555),
                  self.pad("U1", "16")], width=SIG_W)
        T("V3_340", [self.pad("C3", "1"), (23.0, 11.5), (23.0, 12.095),
                     self.pad("U2", "8")], width=SIG_W)

        # ---------------- SET test pad (TP1) ----------------
        T("SET", [self.pad("U1", "11"), (44.0, 15.905),
                  self.pad("TP1", "1")], width=SIG_W)

        # ---------------- ground ----------------
        for x, y in ((42.85, 9.0), (26.0, 11.5), (42.325, 7.0), (29.825, 8.0),
                     (3.0, 12.0), (53.0, 12.0), (3.0, 17.0), (53.0, 17.0),
                     (2.0, 2.0), (53.0, 2.0), (2.0, 25.5), (54.0, 25.5),
                     (16.0, 25.5), (28.0, 2.0), (10.0, 25.0), (42.0, 25.0),
                     (50.0, 25.0), (32.0, 10.0), (45.0, 25.0)):
            V(GND, x, y)
        T(GND, [self.pad("U1", "14"), (40.0, 12.095)], width=SIG_W)
        V(GND, 40.0, 12.095)
        # connector and ESD grounds are handled by the GND pour

    def finish(self):
        path = os.path.join(ROOT, f"{PROJECT}.kicad_pcb")

        def drop_zero_length_edges(board):
            for item in list(board.GetDrawings()):
                if item.GetLayer() != pcbnew.Edge_Cuts:
                    continue
                if item.GetShape() != pcbnew.SHAPE_T_SEGMENT:
                    continue
                s = item.GetStart()
                e = item.GetEnd()
                if s.x == e.x and s.y == e.y:
                    board.Remove(item)

        # KiCad 10 crashes when the zone filler runs on a board that only exists
        # in memory, so write it out and fill the reloaded copy.
        drop_zero_length_edges(self.board)
        pcbnew.SaveBoard(path, self.board)
        board = pcbnew.LoadBoard(path)
        drop_zero_length_edges(board)
        board.BuildConnectivity()
        filler = pcbnew.ZONE_FILLER(board)
        filler.Fill(board.Zones())
        pcbnew.SaveBoard(path, board)


def main():
    b = Builder()
    b.outline()
    b.zones()
    b.texts()
    b.qr_code()
    b.route()
    b.finish()
    print("wrote", os.path.join(ROOT, f"{PROJECT}.kicad_pcb"))


if __name__ == "__main__":
    main()
