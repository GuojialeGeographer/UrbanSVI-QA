"""Tests for configuration module."""

import pytest

from urban_svi_qa.config import GSV_PARAMS, BSV_PARAMS, get_platform_params


class TestConfig:
    """Test suite for configuration module."""

    def test_gsv_params_exist(self):
        """Test that GSV parameters are defined."""
        assert "fov" in GSV_PARAMS
        assert "optimal_interval" in GSV_PARAMS
        assert GSV_PARAMS["fov"] == 90
        assert GSV_PARAMS["optimal_interval"] == 20

    def test_bsv_params_exist(self):
        """Test that BSV parameters are defined."""
        assert "fov" in BSV_PARAMS
        assert "optimal_interval" in BSV_PARAMS
        assert BSV_PARAMS["fov"] == 180
        assert BSV_PARAMS["optimal_interval"] == 30

    def test_get_platform_params_google(self):
        """Test retrieving Google platform parameters."""
        params = get_platform_params("google")
        assert params["fov"] == 90
        assert params["optimal_interval"] == 20

    def test_get_platform_params_baidu(self):
        """Test retrieving Baidu platform parameters."""
        params = get_platform_params("baidu")
        assert params["fov"] == 180
        assert params["optimal_interval"] == 30

    def test_get_platform_params_invalid(self):
        """Test that invalid platform raises error."""
        with pytest.raises(ValueError, match="Unsupported platform"):
            get_platform_params("invalid_platform")

    def test_params_immutable(self):
        """Test that returned params are copies."""
        params = get_platform_params("google")
        params["fov"] = 999
        # Original should not be modified
        assert GSV_PARAMS["fov"] == 90
