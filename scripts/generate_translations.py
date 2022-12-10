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
    "sl": "sl-SI",
    "sr": "sr-RS",
}

known_appliance_ids = ["T999902890777401659617", "F999935286050711425369"]


async def generate():
    username = input("Username: ")
    password = input("Password: ")
    credentials = await login(username, password)

    dirname = os.path.dirname(__file__)
    translations_path = os.path.join(
        dirname, "../custom_components/homewhiz/translations/"
    )

    for short_code in api_languages:
        language = api_languages[short_code]
        print(f"language {language}")
        base_contents_index = await fetch_base_contents_index(credentials, language)
        base_localizations = await fetch_localizations(base_contents_index)
        print(f"Base localizations {len(base_localizations.keys())}")
        translations = {}
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
            appliance_descriptions = generate_descriptions_from_config(appliance_config)

            def localize_key(key: str):
                if key in localizations:
                    return localizations[key]
                return key

            def localize(description: EnumEntityDescription):
                return {
                    option.strKey: localize_key(option.strKey)
                    for option in description.options
                }

            appliance_translations = {
                description.device_class: localize(description)
                for description in appliance_descriptions
                if isinstance(description, EnumEntityDescription)
            }

            translations = mergedeep.merge(
                translations,
                appliance_translations,
                strategy=Strategy.TYPESAFE_ADDITIVE,
            )

        result = {"state": translations}

        file_path = os.path.join(translations_path, f"sensor.{short_code}.json")
        with open(file_path, "w") as outfile:
            json.dump(result, outfile, indent=2)
        print(f"{file_path} Updated")


if __name__ == "__main__":
    asyncio.run(generate())
