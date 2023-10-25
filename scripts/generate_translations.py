"""Generates translation files for the HomeWhiz custom component

Copy the custom_components folder into the scripts folder before running.
Authenticate with your HomeWhiz account (translations are retrieved from HomeWhiz API)
"""
import asyncio
import json
import os
from collections.abc import Mapping, MutableMapping
from typing import Any

import aiohttp
from mergedeep import Strategy, mergedeep  # type: ignore[import]
from translate import Translator  # type: ignore[import]

from custom_components.homewhiz.api import (
    LoginResponse,
    fetch_appliance_contents,
    fetch_base_contents_index,
    fetch_localizations,
    login,
)
from custom_components.homewhiz.appliance_controls import (
    BooleanControl,
    ClimateControl,
    DebugControl,
    DisabledSwingAxisControl,
    EnumControl,
    HvacControl,
    NumericControl,
    SwingAxisControl,
    SwingControl,
    TimeControl,
    WriteBooleanControl,
    WriteEnumControl,
    WriteNumericControl,
    generate_controls_from_config,
)


async def get_file(url: str) -> Any:
    """Get JSON file from url"""
    async with aiohttp.ClientSession() as session:
        async with session.get(
            url,
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
    "ru": "ru-RU",
}

KNOWN_APPLIANCE_IDS = [
    "F999935286050711425369",  # Washing machine
    "F999904668828549174231",  # Oven
    "F999961730155826793828",  # Dishwasher
    "F999931386498761371494",  # Dishwasher
    "F999906704284043631839",  # Washing machine with dryer
    "T999902890777401659617",  # AC
    "F999936350554254966477",  # Advanced AC
]


async def write_translations_file(language_code: str, translations: dict) -> None:
    """Writes translation data for a specific language to a file"""
    dirname = os.path.dirname(__file__)
    translations_path = os.path.join(
        dirname, "../custom_components/homewhiz/translations/"
    )
    file_path = os.path.join(translations_path, f"{language_code}.json")

    with open(file_path, "w") as outfile:
        json.dump(translations, outfile, indent=2)
        outfile.write("\n")

    print(f"{file_path} Updated")


async def generate_translations(credentials: LoginResponse, short_code: str) -> None:
    language = API_LANGUAGES[short_code]
    base_contents_index = await fetch_base_contents_index(credentials, language)
    base_localizations = await fetch_localizations(base_contents_index)
    select_translations: MutableMapping[str, Mapping[str, str]] = {}
    sensor_translations: MutableMapping[str, Mapping[str, str]] = {}
    binary_sensor_translations: MutableMapping[str, Mapping[str, str]] = {}
    climate_translations: MutableMapping[str, Mapping[str, str]] = {}
    switch_translations: MutableMapping[str, Mapping[str, str]] = {}

    # Needed for translate module
    loop = asyncio.get_event_loop()

    # Load base translation from base_translations
    base_translation = {}
    try:
        with open(f"base_translations/{short_code}.json") as fh:
            base_translation = json.load(fh)
    except FileNotFoundError:
        print(f"Could not find {language}.json in folder base_translations!")

    for appliance_id in KNOWN_APPLIANCE_IDS:
        contents = await fetch_appliance_contents(credentials, appliance_id, language)
        appliance_localizations = contents.localization
        appliance_config = contents.config
        print(
            f"{appliance_id} localizations: language {language}: {len(appliance_localizations.keys())}"  # noqa: E501
        )

        # Merge localizations
        localizations = base_localizations | appliance_localizations
        controls = generate_controls_from_config(appliance_config)

        # Filter controls
        #  .select          WriteEnumControl,WriteNumericControl
        select_controls = [
            control
            for control in controls
            if isinstance(control, WriteEnumControl)
            or isinstance(control, WriteNumericControl)  # noqa: E501
            # Untested
            or isinstance(control, SwingAxisControl)
            or isinstance(control, SwingControl)
            or isinstance(control, HvacControl)
        ]
        #  .sensor          DebugControl,EnumControl,NumericControl,TimeControl
        sensor_controls = [
            control
            for control in controls
            if isinstance(control, DebugControl)
            or isinstance(control, EnumControl)
            or isinstance(control, NumericControl)
            or isinstance(control, TimeControl)
            # Untested
            or isinstance(control, DisabledSwingAxisControl)
            and not isinstance(control, WriteEnumControl)
            and not isinstance(control, WriteNumericControl)
        ]
        #  .binary_sensor   BooleanControl,WriteBooleanControl
        binary_sensor_controls = [
            control
            for control in controls
            if isinstance(control, BooleanControl)
            and not isinstance(control, WriteBooleanControl)
        ]

        #  .climate         ClimateControl
        climate_controls = [
            control for control in controls if isinstance(control, ClimateControl)
        ]

        #  .switch          WriteBooleanControl
        switch_controls = [
            control for control in controls if isinstance(control, WriteBooleanControl)
        ]

        def localize_options(control: EnumControl) -> dict[str, str]:
            # Localizes all options for a control
            entity_result: dict[str, str] = {}
            for option in control.options.values():
                # Replace plus (needed for homeassistant friendly name) with +
                # else translation cannot be looked up
                option = option.replace("plus", "+")
                localized = localizations.get(option, option)
                localized = str(localized)
                option = option.replace("+", "plus")

                # Separate values from unites
                # For keys generated in get_bounded_values_options
                # localized = re.sub(r"(\d+)([^0-9\ \-\']+)", r"\1 \2", localized)

                if localized is not None:
                    entity_result[option.lower()] = str(localized)
            return entity_result

        # Translator for localize_name function
        translator = Translator(to_lang=short_code, from_lang="en")
        # Unsure if translator caches translations
        translator_cache: dict[str, str] = {}

        async def localize_name(key: str) -> str:
            # Localizes the entity name
            if key in localizations:
                return localizations[key]
            # Not all translations for entities are provided
            # Therefore, try to translate using google translate
            key = key.replace("_", " ")
            key = key.capitalize()

            # Do not translate for English
            if short_code == "en":
                return key

            # Try to translate name
            # Translate is not asyncio friendly, therefore executor
            if key not in translator_cache:
                translation = await loop.run_in_executor(
                    None, translator.translate, key
                )
                print(
                    f"Translating key '{key}' to language '{short_code}' as: '{translation}'"  # noqa: E501
                )
            else:
                translation = translator_cache[key]
            return translation

        async def create_and_merge_localization(
            localization: MutableMapping[str, Mapping[str, str]],
            controls: list,  # list[Control]
        ) -> MutableMapping[str, Mapping[str, str]]:
            # Localizes all controls and merges them with the localization mapping
            data = {
                f"{control.key.lower()}": {
                    "name": await localize_name(control.key),
                    "state": localize_options(control),
                }
                if hasattr(control, "options")
                else {"name": await localize_name(control.key)}
                for control in controls
            }

            return mergedeep.merge(
                localization,
                data,
                strategy=Strategy.TYPESAFE_ADDITIVE,
            )

        select_translations = await create_and_merge_localization(
            select_translations, select_controls + binary_sensor_controls
        )
        sensor_translations = await create_and_merge_localization(
            sensor_translations,
            select_controls
            + sensor_controls
            + binary_sensor_controls
            + switch_controls,
        )
        binary_sensor_translations = await create_and_merge_localization(
            binary_sensor_translations, binary_sensor_controls
        )
        climate_translations = await create_and_merge_localization(
            climate_translations, climate_controls
        )
        switch_translations = await create_and_merge_localization(
            switch_translations, switch_controls
        )

    # Base translations for config flow
    translations = base_translation

    translations["entity"] = {
        "select": select_translations,
        "sensor": sensor_translations,
        "binary_sensor": binary_sensor_translations,
        "climate": climate_translations,
        "switch": switch_translations,
    }

    await write_translations_file(short_code, translations)


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
