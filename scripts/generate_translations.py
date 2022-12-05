import asyncio
import json

import aiohttp
from dacite import from_dict

from custom_components.homewhiz.appliance_config import ApplianceConfiguration
from custom_components.homewhiz.sensor import (
    generate_descriptions_from_config,
    EnumEntityDescription,
)


async def get_file(address: str):
    async with aiohttp.ClientSession() as session:
        async with session.get(
            address,
        ) as response:
            return json.loads(await response.text())


localization_6_path = "https://s3-eu-west-1.amazonaws.com/procam-contents/LOCALIZATIONS/LOCALIZATION_6/v592/LOCALIZATION_6.en-GB.json"
localization_30_path = "https://s3-eu-west-1.amazonaws.com/procam-contents/LOCALIZATIONS/LOCALIZATION_30/v100/LOCALIZATION_30.en-GB.json"
config_216_path = "https://s3-eu-west-1.amazonaws.com/procam-contents/CONFIGURATIONS/CONFIGURATION_216/v14/CONFIGURATION_216.en-GB.json"


async def generate():
    localizations_6 = (await get_file(localization_6_path))["localizations"]
    localizations_30 = (await get_file(localization_30_path))["localizations"]
    localizations = localizations_6 | localizations_30
    config = from_dict(ApplianceConfiguration, await get_file(config_216_path))

    descriptions = generate_descriptions_from_config(config)

    def localize_key(key: str):
        if key in localizations:
            return localizations[key]
        return key

    def localize(description: EnumEntityDescription):
        return {
            option.strKey: localize_key(option.strKey) for option in description.options
        }

    result = {
        "state": {
            description.device_class: localize(description)
            for description in descriptions
            if isinstance(description, EnumEntityDescription)
        }
    }
    print(json.dumps(result, indent=4))


if __name__ == "__main__":
    asyncio.run(generate())
