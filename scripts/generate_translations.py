import asyncio
import json
import os

import aiohttp
from dacite import from_dict

from custom_components.homewhiz.appliance_config import ApplianceConfiguration
from custom_components.homewhiz.sensor import (
    EnumEntityDescription,
    generate_descriptions_from_config,
)


async def get_file(address: str):
    async with aiohttp.ClientSession() as session:
        async with session.get(
            address,
        ) as response:
            return json.loads(await response.text())


api_languages = {
    "en": "en-GB",
    "tr": "tr-TR",
    "sv": "sv-SE",
    "ro": "ro-RO",
    "fi": "fi-FI",
    "fr": "fr-FR",
    "it": "it-IT",
    "nb": "nb-NO",
    "pl": "pl-PL",
    "de": "de-DE",
    "da": "da-DK",
    "cs": "cs-CZ",
    "es": "es-ES",
    "pt": "pt-PT",
}


def localization_6(language: str):
    return (
        "https://s3-eu-west-1.amazonaws.com/procam-contents"
        f"/LOCALIZATIONS/LOCALIZATION_6/v592/LOCALIZATION_6.{language}.json"
    )


def localization_30(language: str):
    return (
        "https://s3-eu-west-1.amazonaws.com/procam-contents"
        f"/LOCALIZATIONS/LOCALIZATION_30/v100/LOCALIZATION_30.{language}.json"
    )


config_216 = (
    "https://s3-eu-west-1.amazonaws.com/procam-contents"
    "/CONFIGURATIONS/CONFIGURATION_216/v14/CONFIGURATION_216.en-GB.json"
)


async def generate():
    dirname = os.path.dirname(__file__)
    translations_path = os.path.join(
        dirname, "../custom_components/homewhiz/translations/"
    )
    config = from_dict(ApplianceConfiguration, await get_file(config_216))
    descriptions = generate_descriptions_from_config(config)

    for short_code in api_languages:
        language = api_languages[short_code]
        localizations_6 = (await get_file(localization_6(language)))["localizations"]
        localizations_30 = (await get_file(localization_30(language)))["localizations"]
        localizations = localizations_6 | localizations_30

        def localize_key(key: str):
            if key in localizations:
                return localizations[key]
            return key

        def localize(description: EnumEntityDescription):
            return {
                option.strKey: localize_key(option.strKey)
                for option in description.options
            }

        result = {
            "state": {
                description.device_class: localize(description)
                for description in descriptions
                if isinstance(description, EnumEntityDescription)
            }
        }

        file_path = os.path.join(translations_path, f"sensor.{short_code}.json")
        with open(file_path, "w") as outfile:
            json.dump(result, outfile, indent=2)
        print(f"{file_path} Updated")


if __name__ == "__main__":
    asyncio.run(generate())
