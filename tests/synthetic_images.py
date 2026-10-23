"""Synthetic scoreboard images for OCR tests (grayscale uint8 numpy arrays).

Not a test module; import it from tests (pytest puts tests/ on sys.path).
"""

import cv2
import numpy as np

# segments lit per digit: a=top, b=top right, c=bottom right, d=bottom,
# e=bottom left, f=top left, g=middle
_SEGMENTS = {
    "0": "abcdef",
    "1": "bc",
    "2": "abged",
    "3": "abgcd",
    "4": "fgbc",
    "5": "afgcd",
    "6": "afgedc",
    "7": "abc",
    "8": "abcdefg",
    "9": "abcdfg",
}


def seven_segment(
    text: str, height: int = 80, fg: int = 255, bg: int = 0, pad: int = 20
):
    """Render digits, ':' and '.' as a 7-segment LED/LCD display."""
    width = height // 2
    thickness = max(4, height // 9)
    gap = width // 2
    image = np.full(
        (height + 2 * pad, 2 * pad + len(text) * (width + gap)), bg, np.uint8
    )
    x0 = pad
    for char in text:
        if char == ":":
            for y in (pad + height // 3, pad + 2 * height // 3):
                cv2.rectangle(
                    image,
                    (x0, y - thickness // 2),
                    (x0 + thickness, y + thickness // 2),
                    fg,
                    -1,
                )
            x0 += thickness + gap
            continue
        if char == ".":
            cv2.rectangle(
                image,
                (x0, pad + height - thickness),
                (x0 + thickness, pad + height),
                fg,
                -1,
            )
            x0 += thickness + gap
            continue
        y0, mid, t = pad, height // 2, thickness
        corners = {
            "a": ((x0 + t, y0), (x0 + width - t, y0 + t)),
            "d": ((x0 + t, y0 + height - t), (x0 + width - t, y0 + height)),
            "g": ((x0 + t, y0 + mid - t // 2), (x0 + width - t, y0 + mid + t // 2)),
            "f": ((x0, y0 + t), (x0 + t, y0 + mid - t // 2)),
            "b": ((x0 + width - t, y0 + t), (x0 + width, y0 + mid - t // 2)),
            "e": ((x0, y0 + mid + t // 2), (x0 + t, y0 + height - t)),
            "c": ((x0 + width - t, y0 + mid + t // 2), (x0 + width, y0 + height - t)),
        }
        for segment in _SEGMENTS[char]:
            cv2.rectangle(image, *corners[segment], fg, -1)
        x0 += width + gap
    return image


def ghosted_display(
    lit: str,
    ghosted: str,
    height: int = 80,
    lit_gray: int = 255,
    ghost_gray: int = 60,
    bg: int = 0,
    pad: int = 20,
):
    """A 7-segment display showing lit, still glowing the segments of ghosted.

    A dim LED or LCD panel lights the segments that are off a little, so what
    it showed before keeps showing dimly: a board that goes from 80 to 0 reads
    as 80 while the 8's segments still glow. The two strings are aligned on
    the right (a space in lit is a cell that shows only the ghost); neither may
    contain ':' or '.'."""
    cells = max(len(lit), len(ghosted))
    lit, ghosted = lit.rjust(cells), ghosted.rjust(cells)
    # a digit's width and the gap after it, as seven_segment renders them
    cell_width = height // 2 + (height // 2) // 2

    def cell(char, gray):
        if char == " ":
            return np.full((height, cell_width), bg, np.uint8)
        return seven_segment(char, height=height, fg=gray, bg=bg, pad=0)

    image = np.hstack(
        [
            np.maximum(cell(ghost_char, ghost_gray), cell(lit_char, lit_gray))
            for ghost_char, lit_char in zip(ghosted, lit)
        ]
    )
    return cv2.copyMakeBorder(image, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=bg)


def hershey(
    text: str,
    font: int = cv2.FONT_HERSHEY_SIMPLEX,
    scale: float = 3,
    thickness: int = 6,
    fg: int = 255,
    bg: int = 0,
    pad: int = 20,
):
    """Render text with one of OpenCV's built-in Hershey fonts."""
    (text_width, text_height), baseline = cv2.getTextSize(text, font, scale, thickness)
    image = np.full(
        (text_height + baseline + 2 * pad, text_width + 2 * pad), bg, np.uint8
    )
    cv2.putText(
        image, text, (pad, pad + text_height), font, scale, fg, thickness, cv2.LINE_AA
    )
    return image


def binarize(gray):
    """The capture thread's global Otsu binarization."""
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return binary
