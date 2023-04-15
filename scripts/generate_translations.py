import asyncio
import json
import os
import re
from collections.abc import Mapping, MutableMapping
from typing import Any

import aiohttp
from mergedeep import Strategy, mergedeep  # type: ignore[import]

from custom_components.homewhiz import DOMAIN
from custom_components.homewhiz.api import (
    LoginResponse,
    fetch_appliance_contents,
    fetch_base_contents_index,
    fetch_localizations,
    login,
)
from custom_components.homewhiz.appliance_controls import (
    EnumControl,
    WriteEnumControl,
    generate_controls_from_config,
)


async def get_file(address: str) -> Any:
    async with aiohttp.ClientSession() as session:
        async with session.get(
            address,
        ) as response:
            return json.loads(await response.text())


API_LANGUAGES = {
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

KNOWN_APPLIANCE_IDS = [
    "F999935286050711425369",  # Washing machine
    "F999904668828549174231",  # Oven
    "F999961730155826793828",  # Dishwasher
    "F999906704284043631839",  # Washing machine with dryer
    "T999902890777401659617",  # AC
    "F999936350554254966477",  # Advanced AC
]


async def write_translations_file(
    name: str, translations: Mapping[str, Mapping[str, str]]
) -> None:
    dirname = os.path.dirname(__file__)
    translations_path = os.path.join(
        dirname, "../custom_components/homewhiz/translations/"
    )
    file_path = os.path.join(translations_path, f"{name}.json")
    with open(file_path, "w") as outfile:
        json.dump({"state": translations}, outfile, indent=2)
        outfile.write("\n")
    print(f"{file_path} Updated")


async def generate_translations(credentials: LoginResponse, short_code: str) -> None:
    language = API_LANGUAGES[short_code]
    print(f"language {language}")
    base_contents_index = await fetch_base_contents_index(credentials, language)
    base_localizations = await fetch_localizations(base_contents_index)
    select_translations: MutableMapping[str, Mapping[str, str]] = {}
    # Use list and not dict because merge won't work
    # (All translation dicts share the key 'enum' and override each other)
    sensor_translations_list: list[Mapping[str, str]] = []

    def localize_key(key: str) -> str | None:
        if key in localizations:
            return localizations[key]
        return None

    for appliance_id in KNOWN_APPLIANCE_IDS:
        contents = await fetch_appliance_contents(credentials, appliance_id, language)
        appliance_localizations = contents.localization
        appliance_config = contents.config
        print(f"{appliance_id} localizations: {len(appliance_localizations.keys())}")
        localizations = base_localizations | appliance_localizations
        controls = generate_controls_from_config(appliance_config)
        select_controls = [
            control for control in controls if isinstance(control, WriteEnumControl)
        ]
        sensor_controls = [
            control
            for control in controls
            if isinstance(control, EnumControl)
            and not isinstance(control, WriteEnumControl)
        ]

        # To filter out forbidden characters
        # https://stackoverflow.com/questions/15754587/keeping-only-certain-characters-in-a-string-using-python

        def filter_key(key: str) -> str:
            # "need to be [a-z0-9-_]+"
            key = key.lower()
            key = re.sub("[^a-z0-9-_]", "", key)
            # "cannot start or end with a hyphen or underscore
            if key[-1] == "_":
                key = key[:-1]
            return key

        def localize(control: EnumControl) -> dict[str, str]:
            entity_result: dict[str, str] = {}
            for option in control.options.values():
                localized = localize_key(option)
                if localized is not None:
                    entity_result[filter_key(option)] = str(localized)
            return entity_result

        select_translations = mergedeep.merge(
            select_translations,
            {
                f"{DOMAIN}__{filter_key(control.key)}": localize(control)
                for control in select_controls
            },
            strategy=Strategy.TYPESAFE_ADDITIVE,
        )
        # Create list of translations and merge later
        sensor_translations_list.extend(
            # Use enum as class for all sensor entities and select entities
            [localize(control) for control in (select_controls + sensor_controls)]
        )

    # Merge all translations into one dictionary (value of enum key)
    sensor_translations_dict: dict[str, str] = {}
    for translation in sensor_translations_list:
        sensor_translations_dict.update(translation)

    await write_translations_file(f"select.{short_code}", select_translations)
    await write_translations_file(
        f"sensor.{short_code}", {"homewhiz__enum": sensor_translations_dict}
    )


async def start_generate() -> None:
    username = input("Username: ")
    password = input("Password: ")
    credentials = await login(username, password)

    await asyncio.gather(
        *[
            generate_translations(credentials, short_code)
            for short_code in API_LANGUAGES
        ]
    )


if __name__ == "__main__":
    asyncio.run(start_generate())
