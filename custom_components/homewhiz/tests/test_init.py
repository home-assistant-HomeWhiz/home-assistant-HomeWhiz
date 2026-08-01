"""Tests for the entry setup guard in async_setup_entry.

Only the very first branch is driven here: it raises before touching hass
or any coordinator, so a bare Mock standing in for the config entry is
enough.
"""

import asyncio
from unittest.mock import Mock

import pytest
from homeassistant.exceptions import HomeAssistantError

from custom_components.homewhiz import async_setup_entry


def test_missing_ids_raises_home_assistant_error() -> None:
    entry = Mock()
    entry.unique_id = "test"
    entry.data = {}

    with pytest.raises(HomeAssistantError):
        asyncio.run(async_setup_entry(Mock(), entry))
