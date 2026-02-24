"""Tests for gamut boundary validation and color space conversions."""

import pytest
import numpy as np

from src.core.gamut import GamutValidator
from src.core.cielab import lab_to_xyz, xyz_to_lab, lab_to_srgb_hex


@pytest.fixture
def validator():
    return GamutValidator()


class TestGamutValidator:
    """Test that gamut validation correctly identifies real and imaginary colors."""

    def test_neutral_gray_in_gamut(self, validator):
        """L*=50, a*=0, b*=0 is a neutral gray — always in gamut."""
        result = validator.is_in_gamut(
            np.array([50.0]), np.array([0.0]), np.array([0.0])
        )
        assert result[0]

    def test_white_in_gamut(self, validator):
        """L*=100, a*=0, b*=0 is the D65 white point — always in gamut."""
        result = validator.is_in_gamut(
            np.array([100.0]), np.array([0.0]), np.array([0.0])
        )
        assert result[0]

    def test_black_in_gamut(self, validator):
        """L*=0, a*=0, b*=0 is black — in gamut by convention."""
        result = validator.is_in_gamut(
            np.array([0.0]), np.array([0.0]), np.array([0.0])
        )
        assert result[0]

    def test_extreme_values_out_of_gamut(self, validator):
        """L*=50, a*=200, b*=200 is way outside the visual gamut."""
        result = validator.is_in_gamut(
            np.array([50.0]), np.array([200.0]), np.array([200.0])
        )
        assert not result[0]

    def test_extreme_negative_out_of_gamut(self, validator):
        """L*=50, a*=-200, b*=-200 is also outside the visual gamut."""
        result = validator.is_in_gamut(
            np.array([50.0]), np.array([-200.0]), np.array([-200.0])
        )
        assert not result[0]

    def test_moderate_chromatic_in_gamut(self, validator):
        """Mid-range L* with moderate chroma should be in gamut."""
        # These correspond to common, visible colors
        L = np.array([50.0, 70.0, 30.0])
        a = np.array([20.0, -30.0, 10.0])
        b = np.array([-15.0, 20.0, -20.0])
        result = validator.is_in_gamut(L, a, b)
        assert all(result), f"Expected all in-gamut, got {result}"

    def test_batch_mixed(self, validator):
        """Mix of in-gamut and out-of-gamut points."""
        L = np.array([50.0, 50.0, 50.0])
        a = np.array([0.0, 200.0, 10.0])
        b = np.array([0.0, 200.0, -10.0])
        result = validator.is_in_gamut(L, a, b)
        assert result[0]      # neutral gray
        assert not result[1]  # extreme
        assert result[2]      # moderate

    def test_filter_valid(self, validator):
        """filter_valid should return only in-gamut points."""
        L = np.array([50.0, 50.0, 50.0])
        a = np.array([0.0, 200.0, 10.0])
        b = np.array([0.0, 200.0, -10.0])
        L_valid, a_valid, b_valid, mask = validator.filter_valid(L, a, b)
        assert len(L_valid) == 2
        assert mask[0] and not mask[1] and mask[2]


class TestConversionRoundtrip:
    """Test L*a*b* <-> XYZ roundtrip accuracy."""

    def test_neutral_gray_roundtrip(self):
        """Roundtrip conversion should be identity for a neutral gray."""
        L_orig, a_orig, b_orig = 50.0, 0.0, 0.0
        X, Y, Z = lab_to_xyz(
            np.array([L_orig]), np.array([a_orig]), np.array([b_orig])
        )
        L_rt, a_rt, b_rt = xyz_to_lab(X, Y, Z)
        np.testing.assert_allclose(L_rt[0], L_orig, atol=1e-10)
        np.testing.assert_allclose(a_rt[0], a_orig, atol=1e-10)
        np.testing.assert_allclose(b_rt[0], b_orig, atol=1e-10)

    def test_chromatic_roundtrip(self):
        """Roundtrip for chromatic colors."""
        L_orig = np.array([25.0, 50.0, 75.0])
        a_orig = np.array([20.0, -30.0, 10.0])
        b_orig = np.array([-15.0, 40.0, -50.0])
        X, Y, Z = lab_to_xyz(L_orig, a_orig, b_orig)
        L_rt, a_rt, b_rt = xyz_to_lab(X, Y, Z)
        np.testing.assert_allclose(L_rt, L_orig, atol=1e-10)
        np.testing.assert_allclose(a_rt, a_orig, atol=1e-10)
        np.testing.assert_allclose(b_rt, b_orig, atol=1e-10)

    def test_white_point(self):
        """D65 white point should map to L*=100, a*=0, b*=0."""
        L, a, b = xyz_to_lab(
            np.array([95.047]), np.array([100.0]), np.array([108.883])
        )
        np.testing.assert_allclose(L[0], 100.0, atol=1e-4)
        np.testing.assert_allclose(a[0], 0.0, atol=1e-4)
        np.testing.assert_allclose(b[0], 0.0, atol=1e-4)


class TestSrgbHex:
    """Test L*a*b* to sRGB hex conversion."""

    def test_white(self):
        """D65 white should be close to #FFFFFF."""
        hex_val = lab_to_srgb_hex(100.0, 0.0, 0.0)
        assert hex_val == "#FFFFFF"

    def test_black(self):
        """L*=0 should be #000000."""
        hex_val = lab_to_srgb_hex(0.0, 0.0, 0.0)
        assert hex_val == "#000000"

    def test_mid_gray(self):
        """L*=50, a*=0, b*=0 should be a mid-gray."""
        hex_val = lab_to_srgb_hex(50.0, 0.0, 0.0)
        # Mid-gray in sRGB is approximately #777777
        r = int(hex_val[1:3], 16)
        g = int(hex_val[3:5], 16)
        b = int(hex_val[5:7], 16)
        assert r == g == b  # should be neutral
        assert 100 < r < 140  # roughly mid-gray range
