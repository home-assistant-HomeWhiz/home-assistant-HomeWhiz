from unittest.mock import Mock, patch

from custom_components.homewhiz.cloud import (
    HomewhizCloudUpdateCoordinator,
    shadow_payload_to_data,
)


def test_real_shadow_update_decodes_wfa() -> None:
    data = shadow_payload_to_data(
        '{"state": {"reported": {"wfaStartOffset": 26, "wfa": [1, 2, 3, 4]}}}'
    )
    assert data == bytearray([0] * 26 + [1, 2, 3, 4])


def test_default_offset_is_26_when_missing() -> None:
    data = shadow_payload_to_data('{"state": {"reported": {"wfa": [9]}}}')
    assert data == bytearray([0] * 26 + [9])


def test_metadata_only_update_is_ignored() -> None:
    # A metadata-only shadow update (presence/connected, no wfa yet) must not
    # be decoded into a false all-zero device state (issue: momentary state
    # flicker / spurious automation triggers on every cloud reconnect).
    data = shadow_payload_to_data(
        '{"state": {"reported": {"connected": true, "modifiedTime": 1720000000}}}'
    )
    assert data is None


def test_no_reported_state_returns_none() -> None:
    assert shadow_payload_to_data('{"state": null}') is None
    assert shadow_payload_to_data("{}") is None


def _coordinator(cloud_polling: bool | None) -> HomewhizCloudUpdateCoordinator:
    hass = Mock()
    entry = Mock()
    entry.options = {} if cloud_polling is None else {"cloud_polling": cloud_polling}
    coordinator = object.__new__(HomewhizCloudUpdateCoordinator)
    coordinator.hass = hass
    coordinator._hass = hass  # noqa: SLF001
    coordinator._entry = entry  # noqa: SLF001
    coordinator._update_timer_task = None  # noqa: SLF001
    return coordinator


@patch("custom_components.homewhiz.cloud.async_track_time_interval")
def test_active_polling_is_enabled_by_default(mock_track: Mock) -> None:
    coordinator = _coordinator(None)

    coordinator._start_active_polling()  # noqa: SLF001

    mock_track.assert_called_once()


@patch("custom_components.homewhiz.cloud.async_track_time_interval")
def test_active_polling_can_be_disabled(mock_track: Mock) -> None:
    coordinator = _coordinator(False)

    coordinator._start_active_polling()  # noqa: SLF001

    mock_track.assert_not_called()
