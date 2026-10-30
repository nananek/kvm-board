"""Single source of truth for the KVM board design.

Both the schematic and the PCB generator import this module, so the netlist
is guaranteed to be identical between the two.
"""

PROJECT = "kvm-board"
REPO_URL = "https://github.com/nananek/kvm-board"

# ---------------------------------------------------------------------------
# Symbols (library coordinates: +Y is up, as in .kicad_sym files)
# ---------------------------------------------------------------------------
# Each symbol: dict(name, halfw, height, pins=[(side, number, name, etype, y)])
# side: "L" or "R" (pins are only horizontal in this design)

def _eight(y0=8.89, step=2.54, n=8):
    return [y0 - i * step for i in range(n)]


SYMBOLS = {
    "CH9329": dict(
        halfw=7.62, height=10.16,
        pins=[
            ("L", "1", "ACT#", "output", 8.89),
            ("L", "2", "MODE0", "input", 6.35),
            ("L", "3", "MODE1", "input", 3.81),
            ("L", "4", "CFG0", "input", 1.27),
            ("L", "5", "CFG1", "input", -1.27),
            ("L", "6", "RST", "input", -3.81),
            ("L", "7", "TXD", "output", -6.35),
            ("L", "8", "RXD", "input", -8.89),
            ("R", "16", "V33", "passive", 8.89),
            ("R", "15", "VCC", "power_in", 6.35),
            ("R", "14", "GND", "power_in", 3.81),
            ("R", "13", "UD-", "bidirectional", 1.27),
            ("R", "12", "UD+", "bidirectional", -1.27),
            ("R", "11", "SET", "input", -3.81),
            ("R", "10", "DEF", "input", -6.35),
            ("R", "9", "UP", "output", -8.89),
        ],
    ),
    "CH340N": dict(
        halfw=7.62, height=5.08,
        pins=[
            ("L", "1", "UD+", "bidirectional", 3.81),
            ("L", "2", "UD-", "bidirectional", 1.27),
            ("L", "3", "GND", "power_in", -1.27),
            ("L", "4", "RTS#", "output", -3.81),
            ("R", "8", "V3", "passive", 3.81),
            ("R", "7", "RXD", "input", 1.27),
            ("R", "6", "TXD", "output", -1.27),
            ("R", "5", "VCC", "power_in", -3.81),
        ],
    ),
    "USB_C": dict(
        halfw=12.7, height=11.43,
        pins=[
            ("L", "A4", "VBUS", "passive", 10.16),
            ("L", "A9", "VBUS", "passive", 7.62),
            ("L", "B4", "VBUS", "passive", 5.08),
            ("L", "B9", "VBUS", "passive", 2.54),
            ("L", "A1", "GND", "passive", 0.0),
            ("L", "A12", "GND", "passive", -2.54),
            ("L", "B1", "GND", "passive", -5.08),
            ("L", "B12", "GND", "passive", -7.62),
            ("L", "SH", "SHIELD", "passive", -10.16),
            ("R", "A5", "CC1", "passive", 8.89),
            ("R", "B5", "CC2", "passive", 6.35),
            ("R", "A6", "D+", "passive", 3.81),
            ("R", "B6", "D+", "passive", 1.27),
            ("R", "A7", "D-", "passive", -1.27),
            ("R", "B7", "D-", "passive", -3.81),
            ("R", "A8", "SBU1", "passive", -6.35),
            ("R", "B8", "SBU2", "passive", -8.89),
        ],
    ),
    "USBLC6": dict(
        halfw=5.08, height=3.81,
        pins=[
            ("L", "1", "I/O1", "bidirectional", 2.54),
            ("L", "2", "GND", "power_in", 0.0),
            ("L", "3", "I/O2", "bidirectional", -2.54),
            ("R", "6", "I/O1", "bidirectional", 2.54),
            ("R", "5", "VBUS", "passive", 0.0),
            ("R", "4", "I/O2", "bidirectional", -2.54),
        ],
    ),
    "TP": dict(
        halfw=1.27, height=1.27,
        pins=[("L", "1", "~", "passive", 0.0)],
    ),
}

PASSIVES = {
    "R": dict(pins=[("L", "1", "~", "passive", 0.0), ("R", "2", "~", "passive", 0.0)]),
    "C": dict(pins=[("L", "1", "~", "passive", 0.0), ("R", "2", "~", "passive", 0.0)]),
    "D": dict(pins=[("L", "2", "A", "passive", 0.0), ("R", "1", "K", "passive", 0.0)]),
    "LED": dict(pins=[("L", "2", "A", "passive", 0.0), ("R", "1", "K", "passive", 0.0)]),
    "PWR_FLAG": dict(pins=[("B", "1", "pwr", "power_out", 0.0)]),
}

# ---------------------------------------------------------------------------
# Nets
# ---------------------------------------------------------------------------
GND = "GND"
P5V = "+5V"

p = [
    # ref, value, symbol, footprint, lcsc, pin->net
    dict(ref="J1", value="TYPE-C-31-M-12", sym="USB_C",
         fp="KVM:USB_C_Receptacle_HRO_TYPE-C-31-M-12", lcsc="C165948",
         pins={
             "A4": "VBUS_SER", "A9": "VBUS_SER", "B4": "VBUS_SER", "B9": "VBUS_SER",
             "A1": GND, "A12": GND, "B1": GND, "B12": GND, "SH": GND,
             "A5": "CC1_SER", "B5": "CC2_SER",
             "A6": "USB_SER_DP", "B6": "USB_SER_DP",
             "A7": "USB_SER_DM", "B7": "USB_SER_DM",
             "A8": None, "B8": None,
         }),
    dict(ref="J2", value="TYPE-C-31-M-12", sym="USB_C",
         fp="KVM:USB_C_Receptacle_HRO_TYPE-C-31-M-12", lcsc="C165948",
         pins={
             "A4": "VBUS_HID", "A9": "VBUS_HID", "B4": "VBUS_HID", "B9": "VBUS_HID",
             "A1": GND, "A12": GND, "B1": GND, "B12": GND, "SH": GND,
             "A5": "CC1_HID", "B5": "CC2_HID",
             "A6": "USB_HID_DP", "B6": "USB_HID_DP",
             "A7": "USB_HID_DM", "B7": "USB_HID_DM",
             "A8": None, "B8": None,
         }),
    dict(ref="U1", value="CH9329", sym="CH9329",
         fp="KVM:SO-16_3.9x9.9mm_P1.27mm", lcsc="C2838834",
         pins={
             "1": "LED_ACT", "2": None, "3": None, "4": None, "5": None, "6": None,
             "7": "UART_9329_TX", "8": "UART_9329_RX",
             "9": None, "10": None, "11": "SET",
             "12": "USB_HID_DP", "13": "USB_HID_DM", "14": GND, "15": P5V,
             "16": "V33",
         }),
    dict(ref="U2", value="CH340N", sym="CH340N",
         fp="KVM:SO-8_3.9x4.9mm_P1.27mm", lcsc="C2977777",
         pins={
             "1": "USB_SER_DP", "2": "USB_SER_DM", "3": GND, "4": None,
             "5": P5V, "6": "UART_340_TX", "7": "UART_340_RX", "8": "V3_340",
         }),
    dict(ref="D1", value="BAT54WS", sym="D",
         fp="KVM:D_SOD-323", lcsc="C22629",
         pins={"2": "VBUS_SER", "1": P5V}),
    dict(ref="D2", value="BAT54WS", sym="D",
         fp="KVM:D_SOD-323", lcsc="C22629",
         pins={"2": "VBUS_HID", "1": P5V}),
    dict(ref="D3", value="USBLC6-2SC6", sym="USBLC6",
         fp="KVM:SOT-23-6", lcsc="C7519",
         pins={"1": "USB_SER_DP", "6": "USB_SER_DP",
               "3": "USB_SER_DM", "4": "USB_SER_DM",
               "2": GND, "5": "VBUS_SER"}),
    dict(ref="D4", value="USBLC6-2SC6", sym="USBLC6",
         fp="KVM:SOT-23-6", lcsc="C7519",
         # The two USBLC6 channels are electrically identical.  D4 uses
         # I/O1 for D- and I/O2 for D+ so the J2 fanout does not cross.
         pins={"1": "USB_HID_DM", "6": "USB_HID_DM",
               "3": "USB_HID_DP", "4": "USB_HID_DP",
               "2": GND, "5": "VBUS_HID"}),
    dict(ref="R1", value="5.1k", sym="R", fp="KVM:R_0603_1608Metric", lcsc="C23186",
         pins={"1": "CC1_SER", "2": GND}),
    dict(ref="R2", value="5.1k", sym="R", fp="KVM:R_0603_1608Metric", lcsc="C23186",
         pins={"1": "CC2_SER", "2": GND}),
    dict(ref="R3", value="5.1k", sym="R", fp="KVM:R_0603_1608Metric", lcsc="C23186",
         pins={"1": "CC1_HID", "2": GND}),
    dict(ref="R4", value="5.1k", sym="R", fp="KVM:R_0603_1608Metric", lcsc="C23186",
         pins={"1": "CC2_HID", "2": GND}),
    dict(ref="R5", value="1k", sym="R", fp="KVM:R_0603_1608Metric", lcsc="C21190",
         pins={"1": P5V, "2": "LED_A"}),
    dict(ref="LED1", value="KT-0603R", sym="LED", fp="KVM:LED_0603_1608Metric",
         lcsc="C2286", pins={"2": "LED_A", "1": "LED_ACT"}),
    dict(ref="C1", value="100nF", sym="C", fp="KVM:C_0603_1608Metric", lcsc="C14663",
         pins={"1": P5V, "2": GND}),
    dict(ref="C2", value="100nF", sym="C", fp="KVM:C_0603_1608Metric", lcsc="C14663",
         pins={"1": P5V, "2": GND}),
    dict(ref="C3", value="100nF", sym="C", fp="KVM:C_0603_1608Metric", lcsc="C14663",
         pins={"1": "V3_340", "2": GND}),
    dict(ref="C4", value="100nF", sym="C", fp="KVM:C_0603_1608Metric", lcsc="C14663",
         pins={"1": "V33", "2": GND}),
    dict(ref="C5", value="10uF", sym="C", fp="KVM:C_0805_2012Metric", lcsc="C15850",
         pins={"1": P5V, "2": GND}),
    dict(ref="C6", value="100nF", sym="C", fp="KVM:C_0603_1608Metric", lcsc="C14663",
         pins={"1": "VBUS_SER", "2": GND}),
    dict(ref="C7", value="100nF", sym="C", fp="KVM:C_0603_1608Metric", lcsc="C14663",
         pins={"1": "VBUS_HID", "2": GND}),
    # Bare test pads: TP1 = CH9329 SET, TP2 = GND.  Not fitted parts.
    dict(ref="TP1", value="SET", sym="TP", fp="KVM:TestPoint_1P", lcsc="",
         fitted=False, pins={"1": "SET"}),
    dict(ref="TP2", value="GND", sym="TP", fp="KVM:TestPoint_1P", lcsc="",
         fitted=False, pins={"1": GND}),
]
PARTS = p

# UART cross connection
assert PARTS[2]["pins"]["7"] == "UART_9329_TX"   # U1 TXD -> CH340 RXD
assert PARTS[3]["pins"]["7"] == "UART_340_RX"
assert PARTS[2]["pins"]["8"] == "UART_9329_RX"
assert PARTS[3]["pins"]["6"] == "UART_340_TX"
# same net on both sides: rename so labels match
for part in PARTS:
    for k, v in list(part["pins"].items()):
        if v == "UART_340_RX":
            part["pins"][k] = "UART_9329_TX"
        elif v == "UART_340_TX":
            part["pins"][k] = "UART_9329_RX"

NETS = sorted({n for part in PARTS for n in part["pins"].values() if n})
