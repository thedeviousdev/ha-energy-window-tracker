"""Pytest configuration and shared fixtures for Energy Window Tracker tests.

Follows the Home Assistant testing framework:
https://developers.home-assistant.io/docs/development_testing/

- Use hass.config_entries.async_setup(entry_id) to set up the integration.
- Assert entity state via hass.states; assert registry via entity_registry.
- Mock config entries via the mock_config_entry fixture (analogous to HA core MockConfigEntry).
"""

from __future__ import annotations

import pytest

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from custom_components.energy_window_tracker.const import (
    CONF_NAME,
    CONF_SOURCE_ENTITY,
    CONF_SOURCES,
    CONF_WINDOWS,
    CONF_WINDOW_END,
    CONF_WINDOW_NAME,
    CONF_WINDOW_START,
    DOMAIN,
)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations for all tests (required for custom component tests)."""
    yield


@pytest.fixture
def mock_config_entry_data() -> dict:
    """Minimal config entry data (one source, one window)."""
    return {
        CONF_SOURCES: [
            {
                CONF_SOURCE_ENTITY: "sensor.today_load",
                CONF_NAME: "Energy",
                CONF_WINDOWS: [
                    {
                        CONF_WINDOW_NAME: "Peak",
                        CONF_WINDOW_START: "09:00",
                        CONF_WINDOW_END: "17:00",
                    }
                ],
            }
        ]
    }


@pytest.fixture
def mock_config_entry(hass: HomeAssistant, mock_config_entry_data: dict) -> ConfigEntry:
    """Create and add a config entry for testing (analogous to MockConfigEntry in HA core)."""
    entry = ConfigEntry(
        version=1,
        minor_version=0,
        domain=DOMAIN,
        title="Energy Window Tracker",
        data=mock_config_entry_data,
        options={},
        entry_id="test_entry_id",
        source="user",
    )
    entry.add_to_hass(hass)
    return entry
