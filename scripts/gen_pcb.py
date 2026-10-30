"""Generate the kvm-board PCB with pcbnew (KiCad 10 python API).

Layout summary
--------------
Board 56 x 27 mm (fits the inner tray of a Frisk mint tin: 58.8 x 32.8 x 9.1).
J1 = serial (CH340N) Type-C on the left short edge, J2 = HID (CH9329)
Type-C on the right short edge.  Both connectors are sinks (5.1k CC pulldowns).
+5V is diode-OR'ed from both VBUS pins and distributed on the top layer.
GND is a copper pour on both layers.
"""

import os
import sys

import pcbnew

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from design import PROJECT, PARTS, GND, P5V  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FP_DIR = os.path.join(ROOT, "lib", "KVM.pretty")

W, H = 56.0, 27.0
THICKNESS = 1.6

# reference -> (footprint name, x, y, rotation)
PLACE = {
    "J1": ("USB_C_Receptacle_HRO_TYPE-C-31-M-12", 3.629, 14.0, 270),
    "J2": ("USB_C_Receptacle_HRO_TYPE-C-31-M-12", 52.371, 14.0, 90),
    "U2": ("SO-8_3.9x4.9mm_P1.27mm", 19.5, 14.0, 0),
    "U1": ("SO-16_3.9x9.9mm_P1.27mm", 36.5, 14.0, 0),
    "D1": ("D_SOD-323", 11.0, 6.0, 180),
    "D2": ("D_SOD-323", 52.0, 6.0, 0),
    "D3": ("SOT-23-6", 13.0, 13.5, 0),
    "D4": ("SOT-23-6", 43.0, 13.5, 180),
    "R1": ("R_0603_1608Metric", 7.0, 21.5, 0),
    "R2": ("R_0603_1608Metric", 13.0, 8.5, 0),
    "R3": ("R_0603_1608Metric", 46.9, 7.6, 180),
    "R4": ("R_0603_1608Metric", 48.0, 21.5, 180),
    "R5": ("R_0603_1608Metric", 31.0, 4.0, 0),
    "LED1": ("LED_0603_1608Metric", 35.0, 4.0, 180),
    "C1": ("C_0603_1608Metric", 43.675, 9.0, 180),
    "C2": ("C_0603_1608Metric", 15.5, 17.5, 180),
    "C3": ("C_0603_1608Metric", 25.2, 11.5, 0),
    "C4": ("C_0603_1608Metric", 41.5, 7.0, 0),
    "C5": ("C_0805_2012Metric", 29.0, 8.0, 0),
    "C6": ("C_0603_1608Metric", 11.0, 16.2, 0),
    "C7": ("C_0603_1608Metric", 45.0, 16.4, 0),
}

SIG_W = 0.2
PWR_W = 0.3
VIA_D = 0.5
VIA_DRILL = 0.3


def P(x, y):
    return pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y))


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
                        if x0 < 1.0 or x1 > 55.0:
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
        def line(a, c):
            s = pcbnew.PCB_SHAPE(self.board)
            s.SetShape(pcbnew.SHAPE_T_SEGMENT)
            s.SetLayer(pcbnew.Edge_Cuts)
            s.SetStart(P(*a))
            s.SetEnd(P(*c))
            s.SetWidth(pcbnew.FromMM(0.1))
            self.board.Add(s)

        def arc(a, m, c):
            s = pcbnew.PCB_SHAPE(self.board)
            s.SetShape(pcbnew.SHAPE_T_ARC)
            s.SetLayer(pcbnew.Edge_Cuts)
            s.SetArcGeometry(P(*a), P(*m), P(*c))
            s.SetWidth(pcbnew.FromMM(0.1))
            self.board.Add(s)

        r = 2.0
        d = r * 0.41421356
        line((r, 0), (W - r, 0))
        line((W, r), (W, H - r))
        line((W - r, H), (r, H))
        line((0, H - r), (0, r))
        arc((W - r, 0), (W - r + d, r - d), (W, r))
        arc((W, H - r), (W - r + d, H - r + d), (W - r, H))
        arc((r, H), (r - d, H - r + d), (0, H - r))
        arc((0, r), (r - d, r - d), (r, 0))

    def zones(self):
        outline = [(0.3, 0.3), (W - 0.3, 0.3), (W - 0.3, H - 0.3), (0.3, H - 0.3)]
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

        text("SERIAL / CH340", 13.0, 25.0, 1.0)
        text("HID / CH9329", 43.0, 25.0, 1.0)
        text("KVM-BOARD  CH9329EMU-USB replacement", 28.0, 2.4, 0.9, 0.13)
        # pin-1 / polarity marks for datasheet comparison
        text("1", 32.2, 8.2, 0.8)
        text("1", 14.0, 10.6, 0.8)
        text("1", 10.0, 11.0, 0.8)
        text("K", 12.05, 4.6, 0.8)
        text("K", 50.95, 4.6, 0.8)
        text("K", 37.0, 5.2, 0.8)
        # A1 marks: J1 is rotated 270 deg (A1 pad at the top edge), J2 is
        # rotated 90 deg (A1 pad at the bottom edge).  The marks sit outside
        # the 8.94 mm wide body; the 0.3 mm difference clears the footprint's
        # silkscreen outline on each side.
        text("A1", 4.2, 8.8, 0.8)
        text("A1", 52.2, 19.5, 0.8)
        text("U1 CH9329   U2 CH340N", 28.0, 22.5, 0.8, 0.1)
        text("D1,D2 BAT54WS   D3,D4 USBLC6-2SC6", 28.0, 23.6, 0.8, 0.1)

    # -- routing -------------------------------------------------------
    def route(self):
        T = self.track
        V = self.via

        # ---------------- +5V (diode OR of both VBUS) ----------------
        T(P5V, [(12.05, 6.0), (50.95, 6.0)], width=PWR_W)
        # serial VBUS: both VBUS pads -> back layer -> D1 anode
        for num in ("A4", "A9"):
            V("VBUS_SER", *self.pad("J1", num))
        T("VBUS_SER", [self.pad("J1", "A4"), (7.674, 12.0), (4.0, 12.0)],
          layer=pcbnew.B_Cu, width=PWR_W)
        T("VBUS_SER", [self.pad("J1", "A9"), (7.674, 15.8), (4.0, 15.8),
                       (4.0, 6.0), (9.8, 6.0)], layer=pcbnew.B_Cu, width=PWR_W)
        V("VBUS_SER", 9.8, 6.0)
        T("VBUS_SER", [(9.8, 6.0), self.pad("D1", "2")], width=PWR_W)
        # ESD clamp and local decoupling on the same VBUS rail
        T("VBUS_SER", [(4.0, 7.5), (14.8, 7.5), (14.8, 13.5)],
          layer=pcbnew.B_Cu, width=SIG_W)
        V("VBUS_SER", 14.8, 13.5)
        T("VBUS_SER", [(14.8, 13.5), self.pad("D3", "5")], width=SIG_W)
        T("VBUS_SER", [self.pad("J1", "A9"), (10.0, 16.2)],
          layer=pcbnew.B_Cu, width=SIG_W)
        V("VBUS_SER", 10.0, 16.2)
        T("VBUS_SER", [(10.0, 16.2), self.pad("C6", "1")], width=SIG_W)
        T(GND, [self.pad("C6", "2"), (12.0, 17.0)], width=SIG_W)
        V(GND, 12.0, 17.0)

        # HID VBUS
        for num in ("A4", "A9"):
            V("VBUS_HID", *self.pad("J2", num))
        T("VBUS_HID", [self.pad("J2", "A9"), (48.326, 12.0), (52.2, 12.0)], layer=pcbnew.B_Cu, width=PWR_W)
        T("VBUS_HID", [self.pad("J2", "A4"), (48.326, 15.8), (52.2, 15.8),
                       (52.2, 6.5), (51.5, 6.5)], layer=pcbnew.B_Cu, width=PWR_W)
        V("VBUS_HID", 51.5, 6.5)
        T("VBUS_HID", [(51.5, 6.5), self.pad("D2", "2")], width=PWR_W)
        T("VBUS_HID", [(52.2, 8.5), (41.2, 8.5), (41.2, 13.5)],
          layer=pcbnew.B_Cu, width=SIG_W)
        V("VBUS_HID", 41.2, 13.5)
        T("VBUS_HID", [(41.2, 13.5), self.pad("D4", "5")], width=SIG_W)
        T("VBUS_HID", [self.pad("J2", "A4"), (44.0, 16.45)],
          layer=pcbnew.B_Cu, width=SIG_W)
        V("VBUS_HID", 44.0, 16.45)
        T("VBUS_HID", [(44.0, 16.45), self.pad("C7", "1")], width=SIG_W)
        T(GND, [self.pad("C7", "2"), (45.5, 17.2)], width=SIG_W)
        V(GND, 45.5, 17.2)

        # U2 (CH340N) VCC: drop under the data signals on the back layer
        V(P5V, 20.0, 6.0)
        T(P5V, [(20.0, 6.0), (20.0, 18.5)], layer=pcbnew.B_Cu, width=PWR_W)
        V(P5V, 20.0, 18.5)
        T(P5V, [(20.0, 18.5), (22.575, 18.5), self.pad("U2", "5")], width=PWR_W)
        T(P5V, [self.pad("C2", "1"), (14.675, 18.5), (20.0, 18.5)], width=SIG_W)
        # U1 (CH9329) VCC
        T(P5V, [(44.5, 6.0), (44.5, 10.825)], width=PWR_W)
        T(P5V, [(44.5, 10.825), self.pad("U1", "15")], width=PWR_W)
        # decoupling caps + LED
        T(P5V, [(self.pad("C5", "1")[0], 6.0), self.pad("C5", "1")], width=SIG_W)
        T(P5V, [self.pad("R5", "1"), (30.175, 6.0)], width=SIG_W)


        # ---------------- serial port USB ----------------
        T("USB_SER_DP", [self.pad("J1", "A6"), (8.9, 13.75)], width=SIG_W)
        T("USB_SER_DP", [self.pad("J1", "B6"), (8.9, 14.75)], width=SIG_W)
        T("USB_SER_DP", [(8.9, 13.75), (8.9, 14.75)], width=SIG_W)
        T("USB_SER_DP", [(8.9, 13.75), (9.0, 13.75), (9.0, 12.55),
                         self.pad("D3", "1")], width=SIG_W)
        T("USB_SER_DP", [self.pad("D3", "1"), self.pad("D3", "6")], width=SIG_W)
        T("USB_SER_DP", [self.pad("D3", "6"), (15.0, 12.55), (15.0, 12.095),
                         self.pad("U2", "1")], width=SIG_W)
        T("USB_SER_DM", [self.pad("J1", "A7"), (8.4, 14.25)], width=SIG_W)
        V("USB_SER_DM", 8.4, 14.25, size=0.35, drill=0.15)
        T("USB_SER_DM", [self.pad("J1", "B7"), (8.4, 13.25)], width=SIG_W)
        V("USB_SER_DM", 8.4, 13.25, size=0.35, drill=0.15)
        T("USB_SER_DM", [(8.4, 13.25), (8.4, 14.25)], layer=pcbnew.B_Cu, width=SIG_W)
        T("USB_SER_DM", [(8.4, 13.25), (9.3, 13.25), (9.3, 14.45),
                         (10.8, 14.45)], layer=pcbnew.B_Cu, width=SIG_W)
        V("USB_SER_DM", 10.8, 14.45, size=0.35, drill=0.15)
        T("USB_SER_DM", [(10.8, 14.45), self.pad("D3", "3")], width=SIG_W)
        T("USB_SER_DM", [self.pad("D3", "3"), self.pad("D3", "4")], width=SIG_W)
        T("USB_SER_DM", [self.pad("D3", "4"), (15.6, 14.45), (15.6, 13.365),
                         self.pad("U2", "2")], width=SIG_W)

        # ---------------- HID port USB ----------------
        T("USB_HID_DP", [self.pad("J2", "A6"), (47.1, 14.25)], width=SIG_W)
        T("USB_HID_DP", [self.pad("J2", "B6"), (47.1, 13.25)], width=SIG_W)
        T("USB_HID_DP", [(47.1, 13.25), (47.1, 14.25)], width=SIG_W)
        T("USB_HID_DP", [(47.1, 14.25), (47.0, 14.25), (47.0, 14.45),
                         self.pad("D4", "1")], width=SIG_W)
        T("USB_HID_DP", [self.pad("D4", "1"), self.pad("D4", "6")], width=SIG_W)
        T("USB_HID_DP", [self.pad("D4", "6"), (40.5, 14.45), (40.5, 14.635),
                         self.pad("U1", "12")], width=SIG_W)
        T("USB_HID_DM", [self.pad("J2", "A7"), (47.7, 13.75)], width=SIG_W)
        V("USB_HID_DM", 47.7, 13.75, size=0.35, drill=0.15)
        T("USB_HID_DM", [self.pad("J2", "B7"), (47.7, 14.75)], width=SIG_W)
        V("USB_HID_DM", 47.7, 14.75, size=0.35, drill=0.15)
        T("USB_HID_DM", [(47.7, 13.75), (47.7, 15.5)], layer=pcbnew.B_Cu, width=SIG_W)
        T("USB_HID_DM", [(47.7, 15.5), (45.0, 15.5), (45.0, 12.55),
                         (45.2, 12.55)], layer=pcbnew.B_Cu, width=SIG_W)
        V("USB_HID_DM", 45.2, 12.55, size=0.35, drill=0.15)
        T("USB_HID_DM", [(45.2, 12.55), self.pad("D4", "3")], width=SIG_W)
        T("USB_HID_DM", [self.pad("D4", "3"), self.pad("D4", "4")], width=SIG_W)
        T("USB_HID_DM", [self.pad("D4", "4"), (40.3, 12.55), (40.3, 13.365),
                         self.pad("U1", "13")], width=SIG_W)

        # ---------------- CC pulldowns ----------------
        T("CC1_SER", [self.pad("J1", "A5"), (5.2, 12.75), (5.2, 21.0),
                      (6.175, 21.0), self.pad("R1", "1")], width=SIG_W)
        T("CC2_SER", [self.pad("J1", "B5"), (9.0, 15.75), (9.0, 15.2),
                      (10.0, 15.2), (10.0, 13.0)], width=SIG_W)
        V("CC2_SER", 10.0, 13.0, size=0.35, drill=0.15)
        T("CC2_SER", [(10.0, 13.0), (10.0, 11.0)], layer=pcbnew.B_Cu, width=SIG_W)
        V("CC2_SER", 10.0, 11.0, size=0.35, drill=0.15)
        T("CC2_SER", [(10.0, 11.0), (10.0, 8.5), self.pad("R2", "1")], width=SIG_W)
        T("CC1_HID", [self.pad("J2", "A5"), (50.6, 15.25), (50.6, 7.6),
                      (48.2, 7.6), self.pad("R3", "1")], width=SIG_W)
        T("CC2_HID", [self.pad("J2", "B5"), (46.5, 12.25), (46.5, 13.0)],
          width=SIG_W)
        V("CC2_HID", 46.5, 13.0, size=0.35, drill=0.15)
        T("CC2_HID", [(46.5, 13.0), (46.5, 15.0)], layer=pcbnew.B_Cu, width=SIG_W)
        V("CC2_HID", 46.5, 15.0, size=0.35, drill=0.15)
        T("CC2_HID", [(46.5, 15.0), (46.5, 23.0), (48.825, 23.0),
                      (48.825, 21.5), self.pad("R4", "1")], width=SIG_W)

        # ---------------- UART between CH340N and CH9329 ----------------
        T("UART_9329_TX", [self.pad("U2", "6"), (23.5, 14.635), (23.5, 17.8),
                           (32.0, 17.8), (32.0, 18.445), self.pad("U1", "8")],
          width=SIG_W)
        T("UART_9329_RX", [self.pad("U1", "7"), (31.0, 17.175), (31.0, 13.365),
                           self.pad("U2", "7")], width=SIG_W)

        # ---------------- LED (cathode crosses the +5V rail on B.Cu) --------
        T("LED_A", [self.pad("R5", "2"), self.pad("LED1", "2")], width=SIG_W)
        T("LED_ACT", [self.pad("LED1", "1"), (35.825, 5.0)], width=SIG_W)
        V("LED_ACT", 35.825, 5.0)
        T("LED_ACT", [(35.825, 5.0), (35.825, 8.0)], layer=pcbnew.B_Cu, width=SIG_W)
        V("LED_ACT", 35.825, 8.0)
        T("LED_ACT", [(35.825, 8.0), (33.425, 8.0), (33.425, 9.555),
                      self.pad("U1", "1")], width=SIG_W)

        # ---------------- V33 / V3 ----------------
        T("V33", [self.pad("C4", "1"), (40.3, 7.0), (40.3, 9.555),
                  self.pad("U1", "16")], width=SIG_W)
        T("V3_340", [self.pad("C3", "1"), (23.0, 11.5), (23.0, 12.095),
                     self.pad("U2", "8")], width=SIG_W)

        # ---------------- ground ----------------
        for x, y in ((42.85, 9.0),
                     (26.0, 11.5), (42.325, 7.0), (29.825, 8.0), (7.825, 21.5),
                     (13.825, 8.5), (46.075, 7.6), (47.175, 21.5)):
            V(GND, x, y)
        T(GND, [self.pad("U1", "14"), (40.0, 12.095)], width=SIG_W)
        V(GND, 40.0, 12.095)
        T(GND, [self.pad("U2", "3"), (16.0, 14.635), (16.0, 15.2),
                (13.5, 15.2), (13.5, 17.0)], width=SIG_W)
        V(GND, 13.5, 17.0)
        # ESD GND pins
        # connector ground / shield is handled by the GND pour

        for x, y in ((10.6, 13.9), (3.0, 12.0), (53.0, 12.0), (3.0, 17.0), (53.0, 17.0),
                     (2.0, 2.0), (54.0, 2.0), (2.0, 25.5), (54.0, 25.5),
                     (28.0, 25.5), (28.0, 2.0), (10.0, 25.0), (38.0, 25.0),
                     (50.0, 25.0), (32.0, 10.0), (45.0, 25.0)):
            V(GND, x, y)

    def finish(self):
        path = os.path.join(ROOT, f"{PROJECT}.kicad_pcb")
        # KiCad 10 crashes when the zone filler runs on a board that only exists
        # in memory, so write it out and fill the reloaded copy.
        pcbnew.SaveBoard(path, self.board)
        board = pcbnew.LoadBoard(path)
        board.BuildConnectivity()
        filler = pcbnew.ZONE_FILLER(board)
        filler.Fill(board.Zones())
        pcbnew.SaveBoard(path, board)


def main():
    b = Builder()
    b.outline()
    b.zones()
    b.texts()
    b.route()
    b.finish()
    print("wrote", os.path.join(ROOT, f"{PROJECT}.kicad_pcb"))


if __name__ == "__main__":
    main()
