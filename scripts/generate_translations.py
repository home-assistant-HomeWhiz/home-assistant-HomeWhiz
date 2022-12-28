import asyncio
import json
import os

import aiohttp
from mergedeep import Strategy, mergedeep

from custom_components.homewhiz.api import (
    fetch_appliance_contents,
    fetch_base_contents_index,
    fetch_localizations,
    login,
)
from custom_components.homewhiz.select import (
    EnumSelectEntityDescription,
    generate_select_descriptions_from_config,
)
from custom_components.homewhiz.sensor import (
    EnumSensorEntityDescription,
    generate_sensor_descriptions_from_config,
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
    "sl": "sl-SI",
    "sr": "sr-RS",
}

known_appliance_ids = [
    "F999935286050711425369",
    "F999904668828549174231",
    "F999961730155826793828",
    "F999906704284043631839",
]


async def write_translations_file(name: str, translations: dict):
    dirname = os.path.dirname(__file__)
    translations_path = os.path.join(
        dirname, "../custom_components/homewhiz/translations/"
    )
    file_path = os.path.join(translations_path, f"{name}.json")
    with open(file_path, "w") as outfile:
        json.dump({"state": translations}, outfile, indent=2)
        outfile.write("\n")
    print(f"{file_path} Updated")


async def generate():
    username = input("Username: ")
    password = input("Password: ")
    credentials = await login(username, password)

    for short_code in api_languages:
        language = api_languages[short_code]
        print(f"language {language}")
        base_contents_index = await fetch_base_contents_index(credentials, language)
        base_localizations = await fetch_localizations(base_contents_index)
        print(f"Base localizations {len(base_localizations.keys())}")
        select_translations = {}
        sensor_translations = {}
        for appliance_id in known_appliance_ids:
            contents = await fetch_appliance_contents(
                credentials, appliance_id, language
            )
            appliance_localizations = contents.localization
            appliance_config = contents.config
            print(
                f"{appliance_id} localizations: {len(appliance_localizations.keys())}"
            )
            localizations = base_localizations | appliance_localizations
            select_descriptions = [
                description
                for description in generate_select_descriptions_from_config(
                    appliance_config
                )
                if isinstance(description, EnumSelectEntityDescription)
            ]
            sensor_descriptions = [
                description
                for description in generate_sensor_descriptions_from_config(
                    appliance_config
                )
                if isinstance(description, EnumSensorEntityDescription)
            ]

            def localize_key(key: str):
                if key in localizations:
                    return localizations[key]

            def localize(
                description: EnumSelectEntityDescription | EnumSensorEntityDescription,
            ):
                entity_result: dict[str, str] = {}
                for option in description.options:
                    localized = localize_key(option)
                    if localized is not None:
                        entity_result[option] = str(localized)
                return entity_result

            select_translations = mergedeep.merge(
                select_translations,
                {
                    description.device_class: localize(description)
                    for description in select_descriptions
                },
                strategy=Strategy.TYPESAFE_ADDITIVE,
            )
            sensor_translations = mergedeep.merge(
                sensor_translations,
                {
                    description.device_class: localize(description)
                    for description in sensor_descriptions
                },
                strategy=Strategy.TYPESAFE_ADDITIVE,
            )

        await write_translations_file(f"select.{short_code}", select_translations)
        await write_translations_file(f"sensor.{short_code}", sensor_translations)


if __name__ == "__main__":
    asyncio.run(generate())
