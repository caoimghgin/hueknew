#!/usr/bin/env python3
"""Count how many JND seeds fall inside sRGB and Adobe RGB gamuts."""

import csv
import math
from pathlib import Path

# --- Color math ---

def lab_to_xyz(L, a, b):
    """CIE L*a*b* to XYZ (D65 white point)."""
    fy = (L + 16) / 116
    fx = a / 500 + fy
    fz = fy - b / 200

    delta = 6 / 29
    for val in (fx, fy, fz):
        pass  # just need the vars

    def finv(t):
        if t > delta:
            return t ** 3
        return 3 * delta**2 * (t - 4 / 29)

    # D65 white point
    Xn, Yn, Zn = 0.95047, 1.00000, 1.08883
    X = Xn * finv(fx)
    Y = Yn * finv(fy)
    Z = Zn * finv(fz)
    return X, Y, Z


# sRGB matrix (D65): XYZ to linear sRGB
SRGB_MAT = [
    [ 3.2404542, -1.5371385, -0.4985314],
    [-0.9692660,  1.8760108,  0.0415560],
    [ 0.0556434, -0.2040259,  1.0572252],
]

# Adobe RGB (1998) matrix (D65): XYZ to linear Adobe RGB
ADOBE_MAT = [
    [ 2.0413690, -0.5649464, -0.3446944],
    [-0.9692660,  1.8760108,  0.0415560],
    [ 0.0134474, -0.1183897,  1.0154096],
]


def xyz_to_linear_rgb(X, Y, Z, matrix):
    """Multiply XYZ by a 3x3 matrix to get linear RGB."""
    r = matrix[0][0]*X + matrix[0][1]*Y + matrix[0][2]*Z
    g = matrix[1][0]*X + matrix[1][1]*Y + matrix[1][2]*Z
    b = matrix[2][0]*X + matrix[2][1]*Y + matrix[2][2]*Z
    return r, g, b


def in_gamut(X, Y, Z, matrix, tol=1e-6):
    """Check if XYZ is inside an RGB gamut (linear components in [0,1])."""
    r, g, b = xyz_to_linear_rgb(X, Y, Z, matrix)
    return all(-tol <= c <= 1 + tol for c in (r, g, b))


# --- Main ---

csv_path = str(Path(__file__).parent.parent / "data" / "jnd.csv")

total = 0
in_srgb = 0
in_adobe = 0
in_both = 0
in_neither = 0

with open(csv_path, newline="") as f:
    reader = csv.DictReader(f)
    for row in reader:
        L = float(row["L"])
        a = float(row["a"])
        b = float(row["b"])

        X, Y, Z = lab_to_xyz(L, a, b)
        s = in_gamut(X, Y, Z, SRGB_MAT)
        ad = in_gamut(X, Y, Z, ADOBE_MAT)

        total += 1
        if s:
            in_srgb += 1
        if ad:
            in_adobe += 1
        if s and ad:
            in_both += 1
        if not s and not ad:
            in_neither += 1

print(f"Total JND seeds:          {total:>10,}")
print(f"Inside sRGB:              {in_srgb:>10,}  ({100*in_srgb/total:.1f}%)")
print(f"Inside Adobe RGB:         {in_adobe:>10,}  ({100*in_adobe/total:.1f}%)")
print(f"Inside both:              {in_both:>10,}  ({100*in_both/total:.1f}%)")
print(f"Outside both:             {in_neither:>10,}  ({100*in_neither/total:.1f}%)")
print(f"sRGB only (not Adobe):    {in_srgb - in_both:>10,}  ({100*(in_srgb - in_both)/total:.1f}%)")
print(f"Adobe only (not sRGB):    {in_adobe - in_both:>10,}  ({100*(in_adobe - in_both)/total:.1f}%)")
print()
print(f"sRGB covers {100*in_srgb/total:.1f}% of human-distinguishable surface colors")
print(f"Adobe RGB covers {100*in_adobe/total:.1f}% of human-distinguishable surface colors")
