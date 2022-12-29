import json
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from dacite import from_dict
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_point_in_time

from .api import login
from .config_flow import CloudConfig
from .const import DOMAIN
from .homewhiz import Command, HomewhizCoordinator

_LOGGER: logging.Logger = logging.getLogger(__package__)


@dataclass
class Reported:
    connected: bool
    wfaStartOffset: str
    wfaSize: str
    brand: str
    applianceType: str
    model: str
    applianceId: str
    macAddr: str
    wfa: list[int]
    modifiedTime: Optional[int]
    wfaSizeModifiedTime: Optional[int]


@dataclass
class Metadata:
    reported: Reported


@dataclass
class State:
    reported: Reported


@dataclass
class MqttPayload:
    state: State


class HomewhizCloudUpdateCoordinator(HomewhizCoordinator):
    def __init__(
        self,
        hass: HomeAssistant,
        appliance_id: str,
        cloud_config: CloudConfig,
        entry: ConfigEntry,
    ) -> None:
        from awscrt import mqtt

        self._appliance_id = appliance_id
        self._hass = hass
        self._cloud_config = cloud_config
        self.alive = True
        self._mqtt = mqtt
        self._connection: mqtt.Connection | None = None
        self._is_connected = False
        self._entry = entry
        self._is_tuya = self._appliance_id.startswith("T")

        super().__init__(hass, _LOGGER, name=DOMAIN)

    async def connect(self):
        from awscrt.auth import AwsCredentialsProvider
        from awsiot import mqtt_connection_builder

        _LOGGER.info(f"Connecting to {self._appliance_id}")
        credentials = await login(
            self._cloud_config.username, self._cloud_config.password
        )
        expiration = datetime.fromtimestamp(credentials.expiration / 1000)
        _LOGGER.debug(f"Credentials expire at: {expiration}")

        credentials_provider = AwsCredentialsProvider.new_static(
            access_key_id=credentials.accessKey,
            session_token=credentials.sessionToken,
            secret_access_key=credentials.secretKey,
        )
        self._connection = mqtt_connection_builder.websockets_with_default_aws_signing(
            client_id=uuid.uuid1().hex,
            endpoint="ajf7v9dcoe69w-ats.iot.eu-west-1.amazonaws.com",
            region="eu-west-1",
            credentials_provider=credentials_provider,
            on_connection_interrupted=self.on_connection_interrupted,
            on_connection_resumed=self.on_connection_resumed,
        )
        self._connection.connect().result()
        self._is_connected = True
        [subscribe_update, _] = self._connection.subscribe(
            f"$aws/things/{self._appliance_id}/shadow/update/accepted",
            self._mqtt.QoS.AT_LEAST_ONCE,
            lambda topic, payload, dup, qos, retain, **kwargs: self.handle_notify(
                payload
            ),
        )
        _LOGGER.debug(f"Subscribe to update result: {subscribe_update.result()}")

        [subscribe_get, _] = self._connection.subscribe(
            f"$aws/things/{self._appliance_id}/shadow/get/accepted",
            self._mqtt.QoS.AT_LEAST_ONCE,
            lambda topic, payload, dup, qos, retain, **kwargs: self.handle_notify(
                payload
            ),
        )
        _LOGGER.debug(f"Subscribe to get result: {subscribe_get.result()}")

        self.force_read()
        self.get_shadow()

        self._entry.async_on_unload(
            async_track_point_in_time(self.hass, self.refresh_connection, expiration)
        )
        return True

    @callback
    def on_connection_interrupted(self, connection, error, **kwargs):
        _LOGGER.debug(f"Connection interrupted {error}"),
        self._is_connected = False

    @callback
    def on_connection_resumed(self, connection, return_code, session_present):
        _LOGGER.debug("Connection resumed"),
        self._is_connected = True

    @callback
    async def refresh_connection(self):
        _LOGGER.debug("Refreshing connection"),
        old_connection = self._connection
        await self.connect()
        old_connection.disconnect()

    def force_read(self):
        suffix = "/tuyacommand" if self._is_tuya else "/command"
        force_read = {
            "type": "fread" + suffix,
        }
        if self._is_tuya:
            force_read["applianceId"] = self._appliance_id
        [publish, _] = self._connection.publish(
            f"$aws/things/{self._appliance_id}/shadow/get",
            json.dumps(force_read),
            qos=self._mqtt.QoS.AT_MOST_ONCE,
        )
        _LOGGER.debug(f"Force read result: {publish.result()}")

    def get_shadow(self):
        [publish, _] = self._connection.publish(
            f"$aws/things/{self._appliance_id}/shadow/get",
            "{}",
            qos=self._mqtt.QoS.AT_MOST_ONCE,
        )
        _LOGGER.debug(f"Get shadow result: {publish.result()}")

    async def send_command(self, command: Command):
        suffix = "/tuyacommand" if self._is_tuya else "/command"
        obj = {
            "type": "write",
            "prm": f"[{command.index},{command.value}]",
        }
        if self._is_tuya:
            obj["applianceId"] = self._appliance_id
        message = json.dumps(obj)
        assert self._connection is not None
        [publish, _] = self._connection.publish(
            self._appliance_id + suffix,
            message,
            qos=self._mqtt.QoS.AT_LEAST_ONCE,
        )
        _LOGGER.debug(f"Sending command {command.index}:{command.value}")
        _LOGGER.debug(f"Command result: {publish.result()}")

    @callback
    def handle_notify(self, payload: str):
        message = from_dict(MqttPayload, json.loads(payload))
        offset = int(message.state.reported.wfaStartOffset)
        padding = [0 for _ in range(0, offset)]
        data = bytearray(padding + message.state.reported.wfa)
        _LOGGER.debug(f"Message received: {data}")
        self.async_set_updated_data(data)

    @property
    def is_connected(self):
        return self._is_connected

    async def kill(self):
        self._is_connected = False
        self.alive = False
        self._connection.disconnect()
