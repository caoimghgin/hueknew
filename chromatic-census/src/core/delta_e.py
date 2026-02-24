"""CIEDE2000 color difference formula (CIE 142-2001).

Provides both vectorized NumPy and pure-Python scalar implementations.
The vectorized version is the workhorse — it computes ΔE2000 for one
reference point against an array of comparison points in a single call.
"""

import numpy as np


def delta_e_2000(L1, a1, b1, L2, a2, b2, kL=1.0, kC=1.0, kH=1.0):
    """Compute CIEDE2000 color difference (vectorized).

    L1/a1/b1 can be scalars (single reference point).
    L2/a2/b2 can be arrays (batch of comparison points).
    Returns an array of ΔE2000 values.

    Implements the full formula including:
    - Chroma-dependent a* correction
    - Lightness, chroma, and hue weighting functions
    - Hue rotation term for blue region correction
    """
    L1 = np.asarray(L1, dtype=np.float64)
    a1 = np.asarray(a1, dtype=np.float64)
    b1 = np.asarray(b1, dtype=np.float64)
    L2 = np.asarray(L2, dtype=np.float64)
    a2 = np.asarray(a2, dtype=np.float64)
    b2 = np.asarray(b2, dtype=np.float64)

    # Step 1: Compute C'ab and h'ab for both colors
    C1_ab = np.sqrt(a1**2 + b1**2)
    C2_ab = np.sqrt(a2**2 + b2**2)

    C_ab_mean = (C1_ab + C2_ab) / 2.0
    C_ab_mean_pow7 = C_ab_mean**7
    G = 0.5 * (1.0 - np.sqrt(C_ab_mean_pow7 / (C_ab_mean_pow7 + 25.0**7)))

    a1_prime = a1 * (1.0 + G)
    a2_prime = a2 * (1.0 + G)

    C1_prime = np.sqrt(a1_prime**2 + b1**2)
    C2_prime = np.sqrt(a2_prime**2 + b2**2)

    h1_prime = np.degrees(np.arctan2(b1, a1_prime)) % 360.0
    h2_prime = np.degrees(np.arctan2(b2, a2_prime)) % 360.0

    # Step 2: Compute delta L', delta C', delta H'
    delta_L_prime = L2 - L1
    delta_C_prime = C2_prime - C1_prime

    # delta h' computation with wraparound handling
    h_diff = h2_prime - h1_prime
    C_product = C1_prime * C2_prime

    delta_h_prime = np.where(
        C_product == 0.0,
        0.0,
        np.where(
            np.abs(h_diff) <= 180.0,
            h_diff,
            np.where(h_diff > 180.0, h_diff - 360.0, h_diff + 360.0)
        )
    )

    delta_H_prime = 2.0 * np.sqrt(C_product) * np.sin(np.radians(delta_h_prime / 2.0))

    # Step 3: Compute CIEDE2000 weighting functions
    L_prime_mean = (L1 + L2) / 2.0
    C_prime_mean = (C1_prime + C2_prime) / 2.0

    # Mean hue with wraparound handling
    h_sum = h1_prime + h2_prime
    h_prime_mean = np.where(
        C_product == 0.0,
        h_sum,
        np.where(
            np.abs(h_diff) <= 180.0,
            h_sum / 2.0,
            np.where(h_sum < 360.0, (h_sum + 360.0) / 2.0, (h_sum - 360.0) / 2.0)
        )
    )

    T = (1.0
         - 0.17 * np.cos(np.radians(h_prime_mean - 30.0))
         + 0.24 * np.cos(np.radians(2.0 * h_prime_mean))
         + 0.32 * np.cos(np.radians(3.0 * h_prime_mean + 6.0))
         - 0.20 * np.cos(np.radians(4.0 * h_prime_mean - 63.0)))

    S_L = 1.0 + 0.015 * (L_prime_mean - 50.0)**2 / np.sqrt(20.0 + (L_prime_mean - 50.0)**2)
    S_C = 1.0 + 0.045 * C_prime_mean
    S_H = 1.0 + 0.015 * C_prime_mean * T

    # Rotation term for blue region correction
    C_prime_mean_pow7 = C_prime_mean**7
    R_C = 2.0 * np.sqrt(C_prime_mean_pow7 / (C_prime_mean_pow7 + 25.0**7))
    delta_theta = 30.0 * np.exp(-((h_prime_mean - 275.0) / 25.0)**2)
    R_T = -np.sin(np.radians(2.0 * delta_theta)) * R_C

    # Step 4: Final ΔE2000
    term_L = delta_L_prime / (kL * S_L)
    term_C = delta_C_prime / (kC * S_C)
    term_H = delta_H_prime / (kH * S_H)

    delta_E = np.sqrt(term_L**2 + term_C**2 + term_H**2 + R_T * term_C * term_H)

    return delta_E


def delta_e_2000_scalar(L1, a1, b1, L2, a2, b2, kL=1.0, kC=1.0, kH=1.0):
    """Compute CIEDE2000 color difference (pure Python scalar version).

    Used for validation against published test pairs. Slower than the
    vectorized version but easier to audit line-by-line.
    """
    import math

    C1_ab = math.sqrt(a1**2 + b1**2)
    C2_ab = math.sqrt(a2**2 + b2**2)

    C_ab_mean = (C1_ab + C2_ab) / 2.0
    C_ab_mean_pow7 = C_ab_mean**7
    G = 0.5 * (1.0 - math.sqrt(C_ab_mean_pow7 / (C_ab_mean_pow7 + 25.0**7)))

    a1_prime = a1 * (1.0 + G)
    a2_prime = a2 * (1.0 + G)

    C1_prime = math.sqrt(a1_prime**2 + b1**2)
    C2_prime = math.sqrt(a2_prime**2 + b2**2)

    h1_prime = math.degrees(math.atan2(b1, a1_prime)) % 360.0
    h2_prime = math.degrees(math.atan2(b2, a2_prime)) % 360.0

    delta_L_prime = L2 - L1
    delta_C_prime = C2_prime - C1_prime

    C_product = C1_prime * C2_prime
    h_diff = h2_prime - h1_prime

    if C_product == 0.0:
        delta_h_prime = 0.0
    elif abs(h_diff) <= 180.0:
        delta_h_prime = h_diff
    elif h_diff > 180.0:
        delta_h_prime = h_diff - 360.0
    else:
        delta_h_prime = h_diff + 360.0

    delta_H_prime = 2.0 * math.sqrt(C_product) * math.sin(math.radians(delta_h_prime / 2.0))

    L_prime_mean = (L1 + L2) / 2.0
    C_prime_mean = (C1_prime + C2_prime) / 2.0

    h_sum = h1_prime + h2_prime
    if C_product == 0.0:
        h_prime_mean = h_sum
    elif abs(h_diff) <= 180.0:
        h_prime_mean = h_sum / 2.0
    elif h_sum < 360.0:
        h_prime_mean = (h_sum + 360.0) / 2.0
    else:
        h_prime_mean = (h_sum - 360.0) / 2.0

    T = (1.0
         - 0.17 * math.cos(math.radians(h_prime_mean - 30.0))
         + 0.24 * math.cos(math.radians(2.0 * h_prime_mean))
         + 0.32 * math.cos(math.radians(3.0 * h_prime_mean + 6.0))
         - 0.20 * math.cos(math.radians(4.0 * h_prime_mean - 63.0)))

    S_L = 1.0 + 0.015 * (L_prime_mean - 50.0)**2 / math.sqrt(20.0 + (L_prime_mean - 50.0)**2)
    S_C = 1.0 + 0.045 * C_prime_mean
    S_H = 1.0 + 0.015 * C_prime_mean * T

    C_prime_mean_pow7 = C_prime_mean**7
    R_C = 2.0 * math.sqrt(C_prime_mean_pow7 / (C_prime_mean_pow7 + 25.0**7))
    delta_theta = 30.0 * math.exp(-((h_prime_mean - 275.0) / 25.0)**2)
    R_T = -math.sin(math.radians(2.0 * delta_theta)) * R_C

    term_L = delta_L_prime / (kL * S_L)
    term_C = delta_C_prime / (kC * S_C)
    term_H = delta_H_prime / (kH * S_H)

    delta_E = math.sqrt(term_L**2 + term_C**2 + term_H**2 + R_T * term_C * term_H)

    return delta_E
