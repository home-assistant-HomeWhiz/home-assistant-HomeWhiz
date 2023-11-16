import logging

from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .config_flow import EntryData
from .const import DOMAIN
from .homewhiz import HomewhizCoordinator, brand_name_by_code

_LOGGER: logging.Logger = logging.getLogger(__package__)


def build_device_info(unique_name: str, data: EntryData) -> DeviceInfo:
    friendly_name = (
        data.appliance_info.name if data.appliance_info is not None else unique_name
    )
    manufacturer = (
        brand_name_by_code[data.appliance_info.brand]
        if data.appliance_info is not None
        else None
    )
    model = data.appliance_info.model if data.appliance_info is not None else None
    return DeviceInfo(  # type: ignore[typeddict-item]
        identifiers={(DOMAIN, unique_name)},
        name=friendly_name,
        manufacturer=manufacturer,
        model=model,
    )


class HomeWhizEntity(CoordinatorEntity[HomewhizCoordinator]):  # type: ignore[type-arg]
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: HomewhizCoordinator,
        device_name: str,
        entity_key: str,
        data: EntryData,
    ):
        super().__init__(coordinator)
        self.entity_key = entity_key
        self._attr_unique_id = f"{device_name}_{entity_key}"
        self._attr_device_info = build_device_info(device_name, data)
        self._attr_device_class = f"{DOMAIN}__{entity_key}"
        self._localization = data.contents.localization

    async def async_added_to_hass(self) -> None:
        """Call when the entity is added to hass."""
        await super().async_added_to_hass()
        if hasattr(self, "_control"):
            if hasattr(self._control, "my_entity_ids"):
                self._control.my_entity_ids.update({self.entity_id: self.name})
            else:
                setattr(self._control, "my_entity_ids", {self.entity_id: self.name})

    @property
    def available(self) -> bool:
        return self.coordinator.is_connected

    @property
    def translation_key(self) -> str:
        """Translation key for this entity."""

        _LOGGER.debug("Retrieving translation_key %s", self.entity_key.lower())

        return self.entity_key.lower().split("#")[0]  # rstrip("_1234567890")
