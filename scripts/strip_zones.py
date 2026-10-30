"""Write a copy of a KiCad board with every zone removed.

Used by gen_docs_images.sh to plot the routing image without the GND pours.
"""

import sys

import pcbnew


def main():
    src, dst = sys.argv[1], sys.argv[2]
    board = pcbnew.LoadBoard(src)
    for zone in list(board.Zones()):
        board.Remove(zone)
    pcbnew.SaveBoard(dst, board)


if __name__ == "__main__":
    main()
