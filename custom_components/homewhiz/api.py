import datetime
import hashlib
import hmac
import json
import logging
from dataclasses import dataclass
from functools import reduce
from typing import Optional

import aiohttp
from aiohttp import ContentTypeError
from dacite import from_dict

from .appliance_config import ApplianceConfiguration

_LOGGER: logging.Logger = logging.getLogger(__package__)
ALGORITHM = "AWS4-HMAC-SHA256"
REGION = "eu-west-1"
SERVICE = "execute-api"


class RequestError(Exception):
    pass


class LoginError(Exception):
    pass


@dataclass
class IdExchangeResponse:
    appId: str


@dataclass
class LoginResponse:
    accessKey: str
    secretKey: str
    sessionToken: str


@dataclass
class ContentsDescription:
    cid: str
    ctype: str
    ver: int
    lang: str


@dataclass
class ContentsIndexResponse:
    results: list[ContentsDescription]


@dataclass
class Home:
    id: int


@dataclass
class MyHomesResponse:
    data: list[Home]


@dataclass
class ApplianceInfo:
    id: int
    applianceId: str
    brand: int
    model: str
    applianceType: int
    platformType: str
    applianceSerialNumber: str
    name: str
    hsmId: Optional[str]
    connectivity: str = "BT"

    def is_bt(self):
        return self == "BT" or self == "BASICBT"


@dataclass
class HomeResponseData:
    appliances: list[ApplianceInfo]


@dataclass
class ApplianceContents:
    config: ApplianceConfiguration
    localization: dict[str, str]


def sign(key, msg):
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()


def getSignatureKey(key, date_stamp, regionName, serviceName):
    kDate = sign(("AWS4" + key).encode("utf-8"), date_stamp)
    kRegion = sign(kDate, regionName)
    kService = sign(kRegion, serviceName)
    kSigning = sign(kService, "aws4_request")
    return kSigning


async def login(username: str, password: str):
    request_parameters = {"password": password, "username": username}

    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://api.arcelikiot.com/auth/login",
            json=request_parameters,
        ) as response:
            contents = await response.json()
            if not contents["success"]:
                _LOGGER.error(json.dumps(contents, indent=4))
                raise LoginError(contents)
            data = contents["data"]
            return from_dict(LoginResponse, data["credentials"])


async def make_id_exchange_request(device_name: str):
    hsmid = device_name[4:]
    _LOGGER.debug(f"hsmid: {hsmid}")
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"https://idexchange.arcelikiot.com/GetApplianceId?hsmid={hsmid}",
        ) as response:
            if not response.ok:
                _LOGGER.error(await response.text())
                raise RequestError()
            contents = json.loads(await response.text())
            return from_dict(IdExchangeResponse, contents)


async def make_get_contents_request(contents: ContentsDescription):
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"https://s3-eu-west-1.amazonaws.com/procam-contents"
            f"/{contents.ctype}S/{contents.cid}"
            f"/v{contents.ver}"
            f"/{contents.cid}.{contents.lang}.json",
        ) as response:
            if not response.ok:
                _LOGGER.error(await response.text())
                raise RequestError()
            return json.loads(await response.text())


async def make_api_get_request(
    host: str,
    credentials: LoginResponse,
    canonical_uri: str,
    canonical_querystring: str = "",
):
    t = datetime.datetime.utcnow()
    amz_date = t.strftime("%Y%m%dT%H%M%SZ")
    date_stamp = t.strftime("%Y%m%d")  # Date w/o time, used in credential scope
    canonical_headers = (
        f"host:{host}\n"
        + f"x-amz-date:{amz_date}\n"
        + f"x-amz-security-token:{credentials.sessionToken}\n"
    )
    signed_headers = "host;x-amz-date;x-amz-security-token"
    payload_hash = hashlib.sha256(b"").hexdigest()

    canonical_request = (
        f"GET\n"
        f"{canonical_uri}\n"
        f"{canonical_querystring}\n"
        f"{canonical_headers}\n"
        f"{signed_headers}\n"
        f"{payload_hash}"
    )

    _LOGGER.debug(
        "Actual canonical request: {}".format(canonical_request.replace("\n", "\\n"))
    )

    credential_scope = f"{date_stamp}/{REGION}/{SERVICE}/aws4_request"
    string_to_sign = (
        f"{ALGORITHM}\n"
        f"{amz_date}\n"
        f"{credential_scope}\n"
        f"{hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()}"
    )

    # Create the signing key using the function defined above.
    signing_key = getSignatureKey(credentials.secretKey, date_stamp, REGION, SERVICE)
    signature = hmac.new(
        signing_key, string_to_sign.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    authorization_header = (
        f"{ALGORITHM} "
        f"Credential={credentials.accessKey}/{credential_scope}, "
        f"SignedHeaders={signed_headers}, "
        f"Signature={signature}"
    )

    headers = {
        "x-amz-date": amz_date,
        "x-amz-security-token": (credentials.sessionToken),
        "Authorization": authorization_header,
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"https://{host}{canonical_uri}?{canonical_querystring}", headers=headers
        ) as response:
            try:
                contents = await response.json()
                if not contents["success"]:
                    _LOGGER.error(json.dumps(contents, indent=4))
                    raise RequestError(contents)
                return contents
            except ContentTypeError:
                _LOGGER.error(await response.text())
                raise RequestError(contents)


async def fetch_contents_index(
    credentials: LoginResponse, app_id: str, language="en-GB"
):
    response = await make_api_get_request(
        host="api.arcelikiot.com",
        canonical_uri="/procam/contents",
        canonical_querystring=(
            f"applianceId={app_id}&"
            f"ctype=CONFIGURATION%2CLOCALIZATION&"
            f"lang={language}&"
            f"testMode=true"
        ),
        credentials=credentials,
    )
    return from_dict(ContentsIndexResponse, response["data"])


async def fetch_base_contents_index(credentials: LoginResponse, language: str):
    response = await make_api_get_request(
        host="api.arcelikiot.com",
        canonical_uri="/procam/contents/subtype",
        canonical_querystring=(
            f"ctype=LOCALIZATION&"
            f"lang={language}&"
            f"subtype=NEW-HOMEWHIZ&"
            f"testMode=false"
        ),
        credentials=credentials,
    )
    return from_dict(ContentsIndexResponse, response["data"])


async def fetch_localizations(contents_index: ContentsIndexResponse):
    localization_contents = [
        content for content in contents_index.results if content.ctype == "LOCALIZATION"
    ]
    localizations = [
        (await make_get_contents_request(localization))["localizations"]
        for localization in localization_contents
    ]
    return reduce(lambda a, b: a | b, localizations)


async def fetch_appliance_contents(
    credentials: LoginResponse, app_id: str, language="en-GB"
) -> ApplianceContents:
    contents_index = await fetch_contents_index(credentials, app_id, language)
    config_contents = [
        content
        for content in contents_index.results
        if content.ctype == "CONFIGURATION"
    ]

    config = await make_get_contents_request(config_contents[0])
    localization = await fetch_localizations(contents_index)

    return ApplianceContents(
        config=from_dict(ApplianceConfiguration, config), localization=localization
    )


async def fetch_appliance_infos(credentials: LoginResponse):
    resp = await make_api_get_request(
        "smarthome.arcelikiot.com",
        credentials,
        canonical_uri="/my-homes",
    )
    homes = from_dict(MyHomesResponse, resp).data
    appliances = []
    for home in homes:
        home_resp = await make_api_get_request(
            "smarthome.arcelikiot.com",
            credentials,
            canonical_uri=f"/my-homes/{home.id}",
        )
        appliances.extend(from_dict(HomeResponseData, home_resp["data"]).appliances)
    return appliances
