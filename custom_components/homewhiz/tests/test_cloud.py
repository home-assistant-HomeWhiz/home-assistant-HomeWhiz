from custom_components.homewhiz.cloud import shadow_payload_to_data


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
