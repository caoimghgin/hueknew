"""CIELAB color space conversions.

All functions are NumPy-vectorized to accept arrays for batch processing.
Uses CIE D65 standard illuminant as the reference white point.
"""

import numpy as np

from .spectral_data import D65_WHITE_X, D65_WHITE_Y, D65_WHITE_Z

# CIELAB transfer function constants
_DELTA = 6.0 / 29.0
_DELTA_SQ = _DELTA ** 2
_DELTA_CU = _DELTA ** 3


def _f(t):
    """CIELAB forward transfer function (cube root with linear segment)."""
    result = np.empty_like(t, dtype=np.float64)
    mask = t > _DELTA_CU
    result[mask] = np.cbrt(t[mask])
    result[~mask] = t[~mask] / (3.0 * _DELTA_SQ) + 4.0 / 29.0
    return result


def _f_inv(t):
    """CIELAB inverse transfer function."""
    result = np.empty_like(t, dtype=np.float64)
    mask = t > _DELTA
    result[mask] = t[mask] ** 3
    result[~mask] = 3.0 * _DELTA_SQ * (t[~mask] - 4.0 / 29.0)
    return result


def lab_to_xyz(L, a, b):
    """Convert CIE L*a*b* to XYZ tristimulus values.

    Args:
        L, a, b: L*a*b* coordinates (scalars or arrays).

    Returns:
        Tuple of (X, Y, Z) arrays.
    """
    L = np.asarray(L, dtype=np.float64)
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)

    fy = (L + 16.0) / 116.0
    fx = a / 500.0 + fy
    fz = fy - b / 200.0

    X = D65_WHITE_X * _f_inv(fx)
    Y = D65_WHITE_Y * _f_inv(fy)
    Z = D65_WHITE_Z * _f_inv(fz)

    return X, Y, Z


def xyz_to_lab(X, Y, Z):
    """Convert XYZ tristimulus values to CIE L*a*b*.

    Args:
        X, Y, Z: Tristimulus values (scalars or arrays).

    Returns:
        Tuple of (L, a, b) arrays.
    """
    X = np.asarray(X, dtype=np.float64)
    Y = np.asarray(Y, dtype=np.float64)
    Z = np.asarray(Z, dtype=np.float64)

    fx = _f(X / D65_WHITE_X)
    fy = _f(Y / D65_WHITE_Y)
    fz = _f(Z / D65_WHITE_Z)

    L = 116.0 * fy - 16.0
    a = 500.0 * (fx - fy)
    b = 200.0 * (fy - fz)

    return L, a, b


def xyz_to_chromaticity(X, Y, Z):
    """Convert XYZ to CIE 1931 chromaticity coordinates (x, y).

    Args:
        X, Y, Z: Tristimulus values (arrays).

    Returns:
        Tuple of (x, y) chromaticity coordinate arrays.
    """
    total = X + Y + Z
    # Avoid division by zero for black (X=Y=Z=0)
    safe_total = np.where(total > 1e-10, total, 1.0)
    x = np.where(total > 1e-10, X / safe_total, 0.0)
    y = np.where(total > 1e-10, Y / safe_total, 0.0)
    return x, y


def _linear_srgb_to_gamma(c):
    """Apply sRGB gamma curve to linear RGB values."""
    c = np.asarray(c, dtype=np.float64)
    result = np.empty_like(c)
    mask = c <= 0.0031308
    result[mask] = 12.92 * c[mask]
    result[~mask] = 1.055 * np.power(c[~mask], 1.0 / 2.4) - 0.055
    return result


def lab_to_srgb_hex(L, a, b):
    """Convert a single L*a*b* color to its nearest sRGB hex representation.

    Out-of-gamut sRGB values are clamped to [0, 255].

    Args:
        L, a, b: Scalar L*a*b* values.

    Returns:
        Hex string like '#4A7BC3'.
    """
    X, Y, Z = lab_to_xyz(
        np.array([L]), np.array([a]), np.array([b])
    )
    X, Y, Z = X[0] / 100.0, Y[0] / 100.0, Z[0] / 100.0

    # XYZ to linear sRGB (D65, sRGB primaries)
    r_lin = 3.2404542 * X - 1.5371385 * Y - 0.4985314 * Z
    g_lin = -0.9692660 * X + 1.8760108 * Y + 0.0415560 * Z
    b_lin = 0.0556434 * X - 0.2040259 * Y + 1.0572252 * Z

    # Apply gamma
    r = _linear_srgb_to_gamma(r_lin)
    g = _linear_srgb_to_gamma(g_lin)
    b_val = _linear_srgb_to_gamma(b_lin)

    # Clamp and convert to 8-bit
    r_int = int(np.clip(r * 255.0 + 0.5, 0, 255))
    g_int = int(np.clip(g * 255.0 + 0.5, 0, 255))
    b_int = int(np.clip(b_val * 255.0 + 0.5, 0, 255))

    return f"#{r_int:02X}{g_int:02X}{b_int:02X}"
