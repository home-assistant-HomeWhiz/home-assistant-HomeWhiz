"""Tests for the entry setup guard in async_setup_entry.

Only the very first branch is driven here: it raises before touching hass
or any coordinator, so a bare Mock standing in for the config entry is
enough.
"""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest
from homeassistant.exceptions import HomeAssistantError

from custom_components.homewhiz import async_setup_entry, setup_bluetooth


def test_missing_ids_raises_home_assistant_error() -> None:
    entry = Mock()
    entry.unique_id = "test"
    entry.data = {}

    with pytest.raises(HomeAssistantError):
        asyncio.run(async_setup_entry(Mock(), entry))


@patch("custom_components.homewhiz.HomewhizBluetoothUpdateCoordinator")
@patch("custom_components.homewhiz.async_register_callback")
def test_stop_listener_is_registered_for_unload(
    mock_register_callback: Mock, mock_coordinator_cls: Mock
) -> None:
    """A reload without this must not leave an extra listener behind each time."""
    mock_register_callback.return_value = Mock()
    mock_coordinator_cls.return_value = Mock()

    hass = Mock()
    hass.data = {}
    hass.config_entries.async_forward_entry_setups = AsyncMock()
    stop_unsub = Mock()
    hass.bus.async_listen_once = Mock(return_value=stop_unsub)

    entry = Mock()
    entry.unique_id = "00:11:22:33:44:55"
    entry.entry_id = "entry1"
    entry.options.get = Mock(return_value=None)
    registered_unloads: list = []
    entry.async_on_unload = Mock(side_effect=registered_unloads.append)

    result = asyncio.run(setup_bluetooth(entry.unique_id, entry, hass))

    assert result is True
    assert stop_unsub in registered_unloads
