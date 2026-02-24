"""Validate CIEDE2000 implementation against published test pairs.

Test data from: Sharma, Wu, and Dalal (2005),
"The CIEDE2000 Color-Difference Formula: Implementation Notes,
Supplementary Test Data, and Mathematical Observations"

All 34 test pairs must match to 4 decimal places.
"""

import pytest
import numpy as np

from src.core.delta_e import delta_e_2000, delta_e_2000_scalar

# (L1, a1, b1, L2, a2, b2, expected_ΔE2000)
SHARMA_TEST_PAIRS = [
    # Pair 1-5
    (50.0000, 2.6772, -79.7751, 50.0000, 0.0000, -82.7485, 2.0425),
    (50.0000, 3.1571, -77.2803, 50.0000, 0.0000, -82.7485, 2.8615),
    (50.0000, 2.8361, -74.0200, 50.0000, 0.0000, -82.7485, 3.4412),
    (50.0000, -1.3802, -84.2814, 50.0000, 0.0000, -82.7485, 1.0000),
    (50.0000, -1.1848, -84.8006, 50.0000, 0.0000, -82.7485, 1.0000),
    # Pair 6-10
    (50.0000, -0.9009, -85.5211, 50.0000, 0.0000, -82.7485, 1.0000),
    (50.0000, 0.0000, 0.0000, 50.0000, -1.0000, 2.0000, 2.3669),
    (50.0000, -1.0000, 2.0000, 50.0000, 0.0000, 0.0000, 2.3669),
    (50.0000, 2.4900, -0.0010, 50.0000, -2.4900, 0.0009, 7.1792),
    (50.0000, 2.4900, -0.0010, 50.0000, -2.4900, 0.0010, 7.1792),
    # Pair 11-15
    (50.0000, 2.4900, -0.0010, 50.0000, -2.4900, 0.0011, 7.2195),
    (50.0000, 2.4900, -0.0010, 50.0000, -2.4900, 0.0012, 7.2195),
    (50.0000, -0.0010, 2.4900, 50.0000, 0.0009, -2.4900, 4.8045),
    (50.0000, -0.0010, 2.4900, 50.0000, 0.0010, -2.4900, 4.8045),
    (50.0000, -0.0010, 2.4900, 50.0000, 0.0011, -2.4900, 4.7461),
    # Pair 16-20
    (50.0000, 2.5000, 0.0000, 50.0000, 0.0000, -2.5000, 4.3065),
    (50.0000, 2.5000, 0.0000, 73.0000, 25.0000, -18.0000, 27.1492),
    (50.0000, 2.5000, 0.0000, 61.0000, -5.0000, 29.0000, 22.8977),
    (50.0000, 2.5000, 0.0000, 56.0000, -27.0000, -3.0000, 31.9030),
    (50.0000, 2.5000, 0.0000, 58.0000, 24.0000, 15.0000, 19.4535),
    # Pair 21-25
    (50.0000, 2.5000, 0.0000, 50.0000, 3.1736, 0.5854, 1.0000),
    (50.0000, 2.5000, 0.0000, 50.0000, 3.2972, 0.0000, 1.0000),
    (50.0000, 2.5000, 0.0000, 50.0000, 1.8634, 0.5757, 1.0000),
    (50.0000, 2.5000, 0.0000, 50.0000, 3.2592, 0.3350, 1.0000),
    (60.2574, -34.0099, 36.2677, 60.4626, -34.1751, 39.4387, 1.2644),
    # Pair 26-30
    (63.0109, -31.0961, -5.8663, 62.8187, -29.7946, -4.0864, 1.2630),
    (61.2901, 3.7196, -5.3901, 61.4292, 2.2480, -4.9620, 1.8731),
    (35.0831, -44.1164, 3.7933, 35.0232, -40.0716, 1.5901, 1.8645),
    (22.7233, 20.0904, -46.6940, 23.0331, 14.9730, -42.5619, 2.0373),
    (36.4612, 47.8580, 18.3852, 36.2715, 50.5065, 21.2231, 1.4146),
    # Pair 31-34
    (90.8027, -2.0831, 1.4410, 91.1528, -1.6435, 0.0447, 1.4441),
    (90.9257, -0.5406, -0.9208, 88.6381, -0.8985, -0.7239, 1.5381),
    (6.7747, -0.2908, -2.4247, 5.8714, -0.0985, -2.2286, 0.6377),
    (2.0776, 0.0795, -1.1350, 0.9033, -0.0636, -0.5514, 0.9082),
]


class TestDeltaE2000Scalar:
    """Test the pure-Python scalar implementation."""

    @pytest.mark.parametrize("L1,a1,b1,L2,a2,b2,expected", SHARMA_TEST_PAIRS)
    def test_sharma_pairs(self, L1, a1, b1, L2, a2, b2, expected):
        result = delta_e_2000_scalar(L1, a1, b1, L2, a2, b2)
        assert abs(result - expected) < 0.0001, (
            f"Scalar: expected {expected}, got {result:.4f} "
            f"for ({L1},{a1},{b1}) vs ({L2},{a2},{b2})"
        )


class TestDeltaE2000Vectorized:
    """Test the NumPy vectorized implementation."""

    @pytest.mark.parametrize("L1,a1,b1,L2,a2,b2,expected", SHARMA_TEST_PAIRS)
    def test_sharma_pairs(self, L1, a1, b1, L2, a2, b2, expected):
        result = delta_e_2000(L1, a1, b1, L2, a2, b2)
        result_val = float(result)
        assert abs(result_val - expected) < 0.0001, (
            f"Vectorized: expected {expected}, got {result_val:.4f} "
            f"for ({L1},{a1},{b1}) vs ({L2},{a2},{b2})"
        )

    def test_batch_computation(self):
        """Test computing one reference against multiple comparison points."""
        L1, a1, b1 = 50.0, 2.5, 0.0
        # Use pairs 17-20 which share the same reference
        L2 = np.array([73.0, 61.0, 56.0, 58.0])
        a2 = np.array([25.0, -5.0, -27.0, 24.0])
        b2 = np.array([-18.0, 29.0, -3.0, 15.0])
        expected = np.array([27.1492, 22.8977, 31.9030, 19.4535])

        result = delta_e_2000(L1, a1, b1, L2, a2, b2)
        np.testing.assert_allclose(result, expected, atol=0.0001)

    def test_identity(self):
        """Same color should give ΔE = 0."""
        result = delta_e_2000(50.0, 25.0, -10.0, 50.0, 25.0, -10.0)
        assert float(result) == pytest.approx(0.0, abs=1e-10)

    def test_symmetry(self):
        """ΔE(a, b) should equal ΔE(b, a)."""
        result_ab = delta_e_2000(50.0, 2.5, 0.0, 73.0, 25.0, -18.0)
        result_ba = delta_e_2000(73.0, 25.0, -18.0, 50.0, 2.5, 0.0)
        assert float(result_ab) == pytest.approx(float(result_ba), abs=1e-10)


class TestConsistency:
    """Test that scalar and vectorized implementations agree."""

    @pytest.mark.parametrize("L1,a1,b1,L2,a2,b2,expected", SHARMA_TEST_PAIRS)
    def test_scalar_vs_vectorized(self, L1, a1, b1, L2, a2, b2, expected):
        scalar = delta_e_2000_scalar(L1, a1, b1, L2, a2, b2)
        vectorized = float(delta_e_2000(L1, a1, b1, L2, a2, b2))
        assert abs(scalar - vectorized) < 1e-10, (
            f"Scalar ({scalar:.6f}) != Vectorized ({vectorized:.6f})"
        )
