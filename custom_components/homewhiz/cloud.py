import asyncio
import functools
import json
import logging
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from dacite import from_dict
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import (
    async_track_point_in_time,
    async_track_point_in_utc_time,
    async_track_time_interval,
)

from .api import login
from .config_flow import CloudConfig
from .const import DOMAIN
from .homewhiz import Command, HomewhizCoordinator

_LOGGER: logging.Logger = logging.getLogger(__package__)


@dataclass
class Reported:
    connected: bool | str | None = None
    brand: str | int | None = None
    applianceType: str | int | None = None
    model: str | None = None
    applianceId: str | None = None
    macAddr: str | None = None
    wfa: list[int] | None = None
    modifiedTime: int | None = None
    wfaSizeModifiedTime: int | None = None
    wfaSize: str | int | None = None
    wfaStartOffset: str | int = 26


@dataclass
class Metadata:
    reported: Reported | None = None


@dataclass
class State:
    reported: Reported | None = None


@dataclass
class MqttPayload:
    state: State | None = None


class HomewhizCloudUpdateCoordinator(HomewhizCoordinator):
    def __init__(
        self,
        hass: HomeAssistant,
        appliance_id: str,
        cloud_config: CloudConfig,
        entry: ConfigEntry,
    ) -> None:
        from awscrt import mqtt  # noqa: PLC0415

        self._appliance_id = appliance_id
        self._hass = hass
        self._cloud_config = cloud_config
        self.alive = True
        self._mqtt = mqtt
        self._connection: mqtt.Connection | None = None
        self._is_connected = False
        self._entry = entry
        self._is_tuya = self._appliance_id.startswith("T")
        self._update_timer_task: Callable | None = None

        super().__init__(hass, _LOGGER, name=DOMAIN)

    async def connect(self) -> bool:
        from awscrt.auth import AwsCredentialsProvider  # noqa: PLC0415
        from awscrt.exceptions import AwsCrtError  # noqa: PLC0415
        from awsiot import (  # noqa: PLC0415
            mqtt_connection_builder,
        )

        _LOGGER.info("Connecting to %s", self._appliance_id)
        credentials = await login(
            self._cloud_config.username, self._cloud_config.password
        )
        expiration = datetime.fromtimestamp(credentials.expiration / 1000, tz=UTC)
        _LOGGER.debug("Credentials expire at: %s", expiration)

        credentials_provider = AwsCredentialsProvider.new_static(
            access_key_id=credentials.accessKey,
            session_token=credentials.sessionToken,
            secret_access_key=credentials.secretKey,
        )
        loop = asyncio.get_event_loop()
        mqtt_connection_builder_task = loop.run_in_executor(
            None,
            functools.partial(
                mqtt_connection_builder.websockets_with_default_aws_signing,
                client_id=uuid.uuid1().hex,
                endpoint="ajf7v9dcoe69w-ats.iot.eu-west-1.amazonaws.com",
                region="eu-west-1",
                credentials_provider=credentials_provider,
                on_connection_interrupted=self.on_connection_interrupted,
                on_connection_resumed=self.on_connection_resumed,
                clean_session=False,
                keep_alive_secs=1200,
            ),
        )
        connection = await mqtt_connection_builder_task
        self._connection = connection
        try:
            connection_future = connection.connect()
            await loop.run_in_executor(None, connection_future.result)
            _LOGGER.debug("MQTT connection successful")
        except AwsCrtError:
            _LOGGER.exception(
                "Exception during connection to AWS occurred. Will retry in one minute."
            )
            self._entry.async_on_unload(
                async_track_point_in_time(
                    hass=self.hass,
                    action=self.refresh_connection,  # type: ignore[arg-type]
                    point_in_time=datetime.today() + timedelta(minutes=1),
                )
            )
            return False

        self._is_connected = True
        await self._subscribe_to_topics()

        await asyncio.sleep(0.5)
        self.force_read()

        async_track_point_in_utc_time(
            hass=self.hass,
            action=self.refresh_connection,  # type: ignore[arg-type]
            point_in_time=expiration - timedelta(minutes=1),
        )

        if not self._update_timer_task:
            self._update_timer_task = async_track_time_interval(
                hass=self.hass, action=self.force_read, interval=timedelta(minutes=1)
            )
            self.get_shadow()
            _LOGGER.debug("Set hass time interval update")

        return True

    async def _subscribe_to_topics(self) -> None:
        if self._connection is None:
            _LOGGER.warning("Cannot subscribe: connection is None")
            return

        loop = asyncio.get_event_loop()

        [subscribe_update, _] = self._connection.subscribe(
            f"$aws/things/{self._appliance_id}/shadow/update/accepted",
            self._mqtt.QoS.AT_LEAST_ONCE,
            lambda topic, payload, dup, qos, retain, **kwargs: self.handle_notify(
                payload
            ),
        )
        [subscribe_get, _] = self._connection.subscribe(
            f"$aws/things/{self._appliance_id}/shadow/get/accepted",
            self._mqtt.QoS.AT_LEAST_ONCE,
            lambda topic, payload, dup, qos, retain, **kwargs: self.handle_notify(
                payload
            ),
        )

        subscribe_update_result = await loop.run_in_executor(
            None, subscribe_update.result
        )
        subscribe_get_result = await loop.run_in_executor(None, subscribe_get.result)
        _LOGGER.debug("Subscribe to update result: %s", subscribe_update_result)
        _LOGGER.debug("Subscribe to get result: %s", subscribe_get_result)

    @callback
    def on_connection_interrupted(self, error: str, **kwargs: Any) -> None:
        _LOGGER.warning("Connection interrupted: %s", error)
        self._is_connected = False

    @callback
    def on_connection_resumed(
        self, return_code: int, session_present: bool, **kwargs: Any
    ) -> None:
        _LOGGER.info(
            "Connection resumed - return_code: %s, session_present: %s",
            return_code,
            session_present,
        )
        self._is_connected = True

        if not session_present:
            _LOGGER.info("Session not present, resubscribing to topics")
            asyncio.create_task(self._resubscribe_after_resume())  # noqa: RUF006

    async def _resubscribe_after_resume(self) -> None:
        await self._subscribe_to_topics()
        await asyncio.sleep(0.5)
        self.force_read()

    @callback
    async def refresh_connection(self, *args: Any) -> None:
        _LOGGER.debug("Refreshing connection")
        if self._connection is not None:
            loop = asyncio.get_event_loop()
            disconnect_future = self._connection.disconnect()
            await loop.run_in_executor(None, disconnect_future.result)
        await self.connect()

    def _handle_mqtt_disconnect_error(self, e: Exception, action: str) -> None:
        """Handle an MQTT not-connected RuntimeError consistently.

        Logs a WARNING only when the connection state transitions from connected -> disconnected,
        otherwise logs at DEBUG to avoid spamming logs during transient disconnects.
        Marks the internal connection state as disconnected.
        """
        if self._is_connected:
            _LOGGER.warning("%s failed: MQTT connection lost: %s", action, e)
        else:
            _LOGGER.debug("%s attempted while MQTT disconnected: %s", action, e)
        self._is_connected = False

    def force_read(self, *args: Any) -> None:
        if self._connection is None or not self._is_connected:
            _LOGGER.warning("Cannot force read: MQTT connection not available")
            return

        _LOGGER.debug("Forcing read")
        suffix = "/tuyacommand" if self._is_tuya else "/command"
        force_read = {
            "type": "fread" + suffix,
        }
        if self._is_tuya:
            force_read["applianceId"] = self._appliance_id

        try:
            [publish, _] = self._connection.publish(
                f"$aws/things/{self._appliance_id}/shadow/get",
                json.dumps(force_read),
                qos=self._mqtt.QoS.AT_MOST_ONCE,
            )
            result = publish.result(timeout=5.0)
            _LOGGER.debug("Force read result: %s", result)
        except RuntimeError as e:
            if "AWS_ERROR_MQTT_NOT_CONNECTED" in str(e):
                self._handle_mqtt_disconnect_error(e, "Force read")
            else:
                _LOGGER.exception("Force read failed with unexpected error")
                raise
        except Exception as e:  # noqa: BLE001
            _LOGGER.error("Force read failed: %s", e)

    def get_shadow(self, *args: Any) -> None:
        if self._connection is None or not self._is_connected:
            _LOGGER.warning("Cannot get shadow: MQTT connection not available")
            return

        try:
            [publish, _] = self._connection.publish(
                f"$aws/things/{self._appliance_id}/shadow/get",
                "{}",
                qos=self._mqtt.QoS.AT_MOST_ONCE,
            )
            result = publish.result(timeout=5.0)
            _LOGGER.debug("Get shadow result: %s", result)
        except RuntimeError as e:
            if "AWS_ERROR_MQTT_NOT_CONNECTED" in str(e):
                self._handle_mqtt_disconnect_error(e, "Get shadow")
            else:
                _LOGGER.exception("Get shadow failed with unexpected error")
                raise
        except Exception as e:  # noqa: BLE001
            _LOGGER.error("Get shadow failed: %s", e)

    async def send_command(self, command: Command) -> None:
        if self._connection is None or not self._is_connected:
            _LOGGER.warning("Cannot send command: MQTT connection not available")
            return

        suffix = "/tuyacommand" if self._is_tuya else "/command"
        obj = {
            "type": "write",
            "prm": f"[{command.index},{command.value}]",
        }
        if self._is_tuya:
            obj["applianceId"] = self._appliance_id
        message = json.dumps(obj)

        try:
            [publish, _] = self._connection.publish(
                self._appliance_id + suffix,
                message,
                qos=self._mqtt.QoS.AT_LEAST_ONCE,
            )
            _LOGGER.debug("Sending command %s:%s", command.index, command.value)
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None, functools.partial(publish.result, timeout=5.0)
            )
            _LOGGER.debug("Command sent successfully")
            # Request updated state after command is sent to ensure Home Assistant
            # reflects the change immediately, mimicking the HomeWhiz app behavior
            await asyncio.sleep(0.5)
            self.force_read()
        except RuntimeError as e:
            if "AWS_ERROR_MQTT_NOT_CONNECTED" in str(e):
                self._handle_mqtt_disconnect_error(e, "Send command")
            else:
                _LOGGER.exception("Send command failed with unexpected error")
                raise
        except Exception as e:  # noqa: BLE001
            _LOGGER.error("Failed to send command: %s", e)

    @callback
    def handle_notify(self, payload: str) -> None:
        _LOGGER.debug("Handling notify")
        _LOGGER.debug("Payload: %s", payload)
        try:
            message = from_dict(MqttPayload, json.loads(payload))
            if message.state and message.state.reported:
                offset = int(message.state.reported.wfaStartOffset or 26)
                wfa = message.state.reported.wfa or []
                padding = [0 for _ in range(offset)]
                data = bytearray(padding + wfa)
                _LOGGER.debug("Message received: %s", data)
                self.hass.loop.call_soon_threadsafe(self.async_set_updated_data, data)
        except Exception as e:  # noqa: BLE001
            _LOGGER.error("Error handling notify: %s", e)

    @property
    def is_connected(self) -> bool:
        return self._is_connected

    async def kill(self) -> None:
        self._is_connected = False
        self.alive = False
        if self._connection is not None:
            loop = asyncio.get_event_loop()
            disconnect_future = self._connection.disconnect()
            await loop.run_in_executor(None, disconnect_future.result)
        if self._update_timer_task:
            self._update_timer_task()
            self._update_timer_task = None
