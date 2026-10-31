"""Generate kvm-board.kicad_sch (KiCad 8/9/10 compatible S-expression)."""

import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from design import PROJECT, SYMBOLS, PASSIVES, PARTS, NETS  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT_UUID = "0e6e9d0a-6a7b-4f4e-9d3a-6f3f5c2b1a01"


def u():
    return str(uuid.uuid4())


def fmt(v):
    s = f"{v:.4f}".rstrip("0").rstrip(".")
    return s if s not in ("", "-0") else "0"


# ---------------------------------------------------------------------------
# symbol library text
# ---------------------------------------------------------------------------
def symbol_pins(sym):
    if sym in SYMBOLS:
        return SYMBOLS[sym]["pins"], SYMBOLS[sym]["halfw"], SYMBOLS[sym]["height"]
    return PASSIVES[sym]["pins"], 1.27, 1.27


def graphic(name, sym):
    if sym == "TP":
        return (
            '      (circle (center 0 0) (radius 1.27) '
            '(stroke (width 0.254) (type default)) (fill (type none)))\n'
        )
    if sym in SYMBOLS:
        hw = SYMBOLS[sym]["halfw"]
        hh = SYMBOLS[sym]["height"]
        return (
            f'      (rectangle (start {fmt(-hw)} {fmt(hh)}) (end {fmt(hw)} {fmt(-hh)}) '
            f'(stroke (width 0.254) (type default)) (fill (type background)))\n'
        )
    if sym in ("R", "C"):
        return (
            '      (rectangle (start -2.54 1.016) (end 2.54 -1.016) '
            '(stroke (width 0.254) (type default)) (fill (type none)))\n'
        )
    if sym in ("D", "LED"):
        s = (
            '      (polyline (pts (xy -1.27 1.27) (xy -1.27 -1.27) (xy 1.27 0) (xy -1.27 1.27)) '
            '(stroke (width 0.254) (type default)) (fill (type none)))\n'
            '      (polyline (pts (xy 1.27 1.27) (xy 1.27 -1.27)) '
            '(stroke (width 0.254) (type default)) (fill (type none)))\n'
        )
        if sym == "LED":
            s += (
                '      (polyline (pts (xy -0.5 2.0) (xy 0.6 3.1)) (stroke (width 0.2) (type default)) (fill (type none)))\n'
                '      (polyline (pts (xy 0.6 3.1) (xy 0.1 2.9) (xy 0.4 2.4) (xy 0.6 3.1)) (stroke (width 0.2) (type default)) (fill (type none)))\n'
                '      (polyline (pts (xy 0.5 2.0) (xy 1.6 3.1)) (stroke (width 0.2) (type default)) (fill (type none)))\n'
                '      (polyline (pts (xy 1.6 3.1) (xy 1.1 2.9) (xy 1.4 2.4) (xy 1.6 3.1)) (stroke (width 0.2) (type default)) (fill (type none)))\n'
            )
        return s
    if sym == "PWR_FLAG":
        return (
            '      (polyline (pts (xy 0 0) (xy 0 1.27) (xy -0.762 1.27) (xy 0 2.54) (xy 0.762 1.27) (xy 0 1.27)) '
            '(stroke (width 0.254) (type default)) (fill (type none)))\n'
        )
    raise ValueError(sym)


def lib_symbol(sym):
    pins, hw, hh = symbol_pins(sym)
    name = sym
    s = f'''    (symbol "kvm:{name}"
      (pin_names (offset 1.016))
      (exclude_from_sim no)
      (in_bom yes)
      (on_board yes)
      (property "Reference" "U" (at 0 {fmt(hh + 2.54)} 0) (effects (font (size 1.27 1.27))))
      (property "Value" "{name}" (at 0 {fmt(-hh - 2.54)} 0) (effects (font (size 1.27 1.27))))
      (property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
      (property "Datasheet" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
      (property "LCSC" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
      (symbol "{name}_0_1"
{graphic(name, sym)}      )
      (symbol "{name}_1_1"
'''
    for side, num, pname, etype, y in pins:
        if side == "L":
            x, ang = -hw - 2.54, 0
        elif side == "R":
            x, ang = hw + 2.54, 180
        elif side == "B":
            x, ang = 0, 90
        else:
            raise ValueError(side)
        s += (
            f'        (pin {etype} line (at {fmt(x)} {fmt(y)} {ang}) (length 2.54)\n'
            f'          (name "{pname}" (effects (font (size 1.27 1.27))))\n'
            f'          (number "{num}" (effects (font (size 1.27 1.27)))))\n'
        )
    s += "      )\n    )\n"
    return s


# ---------------------------------------------------------------------------
# schematic layout
# ---------------------------------------------------------------------------
LAYOUT = {
    "J1": (76.2, 88.9), "U2": (139.7, 88.9), "U1": (215.9, 88.9), "J2": (299.72, 88.9),
    "R1": (50.8, 170.18), "R2": (95.25, 170.18), "R3": (139.7, 170.18), "R4": (184.15, 170.18),
    "C1": (50.8, 203.2), "C2": (95.25, 203.2), "C3": (139.7, 203.2), "C4": (184.15, 203.2),
    "C5": (228.6, 203.2), "C6": (274.32, 203.2), "C7": (320.04, 203.2),
    "D1": (50.8, 238.76), "D2": (95.25, 238.76), "D3": (139.7, 238.76), "D4": (184.15, 238.76),
    "R5": (50.8, 264.16), "LED1": (95.25, 264.16),
    "TP1": (215.9, 139.7), "TP2": (215.9, 149.86),
}

STUB = 3.81


def pin_sheet_pos(sx, sy, side, x, y):
    # library +Y is up, schematic +Y is down
    return (sx + x, sy - y)


def main():
    out = []
    out.append("(kicad_sch\n")
    out.append("  (version 20231120)\n")
    out.append('  (generator "eeschema")\n')
    out.append('  (generator_version "8.0")\n')
    out.append(f'  (uuid "{ROOT_UUID}")\n')
    out.append('  (paper "A3")\n')
    out.append("  (title_block\n")
    out.append('    (title "CH9329 USB KVM emulator board")\n')
    out.append('    (rev "A")\n')
    out.append('    (comment 1 "UART(USB serial) to USB HID keyboard/mouse")\n')
    out.append('    (comment 2 "Fits the measured FRISK case: 66.0 x 31.4 mm")\n')
    out.append("  )\n")

    # --- lib symbols (only those used) ---
    used = []
    for part in PARTS:
        if part["sym"] not in used:
            used.append(part["sym"])
    out.append("  (lib_symbols\n")
    for sym in used:
        out.append(lib_symbol(sym))
    if "PWR_FLAG" not in used:
        out.append(lib_symbol("PWR_FLAG"))
    out.append("  )\n")

    # --- design notes ---
    out.append(f'  (text "UART: U2.TXD(6) -> U1.RXD(8), U1.TXD(7) -> U2.RXD(7)" (at 177.8 69.85 0) (effects (font (size 1.2 1.2))))\n')
    out.append(f'  (text "MODE0/1, CFG0/1, SET, DEF, RST: internal pull-up/pull-down -> Mode 0, protocol, 9600 bps" (at 205.74 114.3 0) (effects (font (size 1.2 1.2))))\n')
    out.append(f'  (text "TP1=SET, TP2=GND: short them while changing the CH9329 settings" (at 152.4 134.62 0) (effects (font (size 1.2 1.2))))\n')
    # --- flags ---
    # --- part instances ---
    for part in PARTS:
        sx, sy = LAYOUT[part["ref"]]
        pins, hw, hh = symbol_pins(part["sym"])
        out.append(f'  (symbol (lib_id "kvm:{part["sym"]}") (at {fmt(sx)} {fmt(sy)} 0) (unit 1)\n')
        out.append("    (exclude_from_sim no) (in_bom yes) (on_board yes) (dnp no)\n")
        out.append(f'    (uuid "{u()}")\n')
        out.append(f'    (property "Reference" "{part["ref"]}" (at {fmt(sx)} {fmt(sy - hh - 4.5)} 0) (effects (font (size 1.27 1.27))))\n')
        out.append(f'    (property "Value" "{part["value"]}" (at {fmt(sx)} {fmt(sy - hh - 1.8)} 0) (effects (font (size 1.27 1.27))))\n')
        out.append(f'    (property "Footprint" "{part["fp"]}" (at {fmt(sx)} {fmt(sy)} 0) (effects (font (size 1.27 1.27)) hide))\n')
        out.append(f'    (property "Datasheet" "" (at {fmt(sx)} {fmt(sy)} 0) (effects (font (size 1.27 1.27)) hide))\n')
        out.append(f'    (property "LCSC" "{part["lcsc"]}" (at {fmt(sx)} {fmt(sy)} 0) (effects (font (size 1.27 1.27)) hide))\n')
        for side, num, pname, etype, y in pins:
            out.append(f'    (pin "{num}" (uuid "{u()}"))\n')
        out.append(f'    (instances (project "{PROJECT}" (path "/{ROOT_UUID}" (reference "{part["ref"]}") (unit 1))))\n')
        out.append("  )\n")

        # pin stubs + labels / no-connects
        for side, num, pname, etype, y in pins:
            if part["sym"] == "USBLC6":
                lx = -SYMBOLS["USBLC6"]["halfw"] - 2.54 if side == "L" else SYMBOLS["USBLC6"]["halfw"] + 2.54
            elif part["sym"] in SYMBOLS:
                lx = -SYMBOLS[part["sym"]]["halfw"] - 2.54 if side == "L" else SYMBOLS[part["sym"]]["halfw"] + 2.54
            else:
                lx = -3.81 if side == "L" else 3.81
            px, py = pin_sheet_pos(sx, sy, side, lx, y)
            net = part["pins"].get(num)
            if net is None:
                out.append(f'  (no_connect (at {fmt(px)} {fmt(py)}) (uuid "{u()}"))\n')
                continue
            if side == "L":
                ex = px - STUB
                just = "right"
            elif side == "R":
                ex = px + STUB
                just = "left"
            else:
                ey = py + STUB
                ex, just = px, "left"
            if side == "B":
                out.append(f'  (wire (pts (xy {fmt(px)} {fmt(py)}) (xy {fmt(ex)} {fmt(py + STUB)})) (stroke (width 0) (type default)) (uuid "{u()}"))\n')
                out.append(f'  (label "{net}" (at {fmt(ex)} {fmt(py + STUB)} 0) (effects (font (size 1.27 1.27)) (justify {just} bottom)) (uuid "{u()}"))\n')
            else:
                out.append(f'  (wire (pts (xy {fmt(px)} {fmt(py)}) (xy {fmt(ex)} {fmt(py)})) (stroke (width 0) (type default)) (uuid "{u()}"))\n')
                out.append(f'  (label "{net}" (at {fmt(ex)} {fmt(py)} 0) (effects (font (size 1.27 1.27)) (justify {just} bottom)) (uuid "{u()}"))\n')

    # --- PWR_FLAG on +5V and GND ---
    for net, x, y, flagref in (("+5V", 152.4, 254, "#FLG01"), ("GND", 203.2, 254, "#FLG02")):
        sx, sy = x, y
        out.append(f'  (symbol (lib_id "kvm:PWR_FLAG") (at {fmt(sx)} {fmt(sy)} 0) (unit 1)\n')
        out.append("    (exclude_from_sim no) (in_bom no) (on_board no) (dnp no)\n")
        out.append(f'    (uuid "{u()}")\n')
        out.append(f'    (property "Reference" "{flagref}" (at {fmt(sx)} {fmt(sy - 3)} 0) (effects (font (size 1.27 1.27)) hide))\n')
        out.append(f'    (property "Value" "PWR_FLAG" (at {fmt(sx)} {fmt(sy + 4)} 0) (effects (font (size 1.27 1.27))))\n')
        out.append(f'    (property "Footprint" "" (at {fmt(sx)} {fmt(sy)} 0) (effects (font (size 1.27 1.27)) hide))\n')
        out.append(f'    (property "Datasheet" "" (at {fmt(sx)} {fmt(sy)} 0) (effects (font (size 1.27 1.27)) hide))\n')
        out.append(f'    (pin "1" (uuid "{u()}"))\n')
        out.append(f'    (instances (project "{PROJECT}" (path "/{ROOT_UUID}" (reference "{flagref}") (unit 1))))\n')
        out.append("  )\n")
        out.append(f'  (wire (pts (xy {fmt(sx)} {fmt(sy)}) (xy {fmt(sx)} {fmt(sy + STUB)})) (stroke (width 0) (type default)) (uuid "{u()}"))\n')
        out.append(f'  (label "{net}" (at {fmt(sx)} {fmt(sy + STUB)} 0) (effects (font (size 1.27 1.27)) (justify left bottom)) (uuid "{u()}"))\n')

    out.append('  (sheet_instances (path "/" (page "1")))\n')
    out.append(")\n")

    path = os.path.join(ROOT, f"{PROJECT}.kicad_sch")
    with open(path, "w") as f:
        f.write("".join(out))
    print("wrote", path)

    # standalone symbol library (for editing in the symbol editor)
    symlib = ["(kicad_symbol_lib (version 20231120) (generator \"kicad_symbol_editor\") (generator_version \"8.0\")\n"]
    for sym in used + ["PWR_FLAG"]:
        symlib.append(lib_symbol(sym).replace(f'"{PROJECT}:{sym}"', f'"{sym}"'))
    symlib.append(")\n")
    os.makedirs(os.path.join(ROOT, "lib"), exist_ok=True)
    with open(os.path.join(ROOT, "lib", "kvm.kicad_sym"), "w") as f:
        f.write("".join(symlib))

    with open(os.path.join(ROOT, "fp-lib-table"), "w") as f:
        f.write('(fp_lib_table\n  (version 7)\n  (lib (name "KVM")(type "KiCad")(uri "${KIPRJMOD}/lib/KVM.pretty")(options "")(descr "KVM board footprints"))\n)\n')
    with open(os.path.join(ROOT, "sym-lib-table"), "w") as f:
        f.write('(sym_lib_table\n  (version 7)\n  (lib (name "kvm")(type "KiCad")(uri "${KIPRJMOD}/lib/kvm.kicad_sym")(options "")(descr "KVM board symbols"))\n)\n')


if __name__ == "__main__":
    main()
