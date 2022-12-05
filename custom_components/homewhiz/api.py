import datetime
import hashlib
import hmac
import json
import logging

import aiohttp
from aiohttp import ContentTypeError

_LOGGER: logging.Logger = logging.getLogger(__package__)


class RequestError(Exception):
    pass


class LoginError(Exception):
    pass


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
            return data["credentials"]


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
            return contents


async def make_get_config_request(contents: dict):
    configuration_id = contents["cid"]
    configuration_version = contents["ver"]
    lang = contents["lang"]
    ctype = contents["ctype"]
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"https://s3-eu-west-1.amazonaws.com/procam-contents"
            f"/{ctype}S/{configuration_id}"
            f"/v{configuration_version}"
            f"/{configuration_id}.{lang}.json",
        ) as response:
            if not response.ok:
                _LOGGER.error(await response.text())
                raise RequestError()
            return json.loads(await response.text())


async def make_api_get_request(
    host: str, credentials: dict, canonical_uri: str, canonical_querystring: str
):
    accessKey = credentials["accessKey"]
    secretKey = credentials["secretKey"]
    sessionToken = credentials["sessionToken"]
    t = datetime.datetime.utcnow()
    amz_date = t.strftime("%Y%m%dT%H%M%SZ")
    date_stamp = t.strftime("%Y%m%d")  # Date w/o time, used in credential scope
    canonical_headers = (
        f"host:{host}\n"
        + f"x-amz-date:{amz_date}\n"
        + f"x-amz-security-token:{sessionToken}\n"
    )
    signed_headers = "host;x-amz-date;x-amz-security-token"
    payload_hash = hashlib.sha256("".encode("utf-8")).hexdigest()

    canonical_request = (
        f"GET\n"
        f"{canonical_uri}\n"
        f"{canonical_querystring}\n"
        f"{canonical_headers}\n"
        f"{signed_headers}\n"
        f"{payload_hash}"
    )

    _LOGGER.debug(
        "Actual canonical request: {0}".format(canonical_request.replace("\n", "\\n"))
    )
    algorithm = "AWS4-HMAC-SHA256"
    region = "eu-west-1"
    service = "execute-api"
    credential_scope = f"{date_stamp}/{region}/{service}/aws4_request"
    string_to_sign = (
        f"{algorithm}\n"
        f"{amz_date}\n"
        f"{credential_scope}\n"
        f"{hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()}"
    )

    # Create the signing key using the function defined above.
    signing_key = getSignatureKey(secretKey, date_stamp, region, service)
    signature = hmac.new(
        signing_key, string_to_sign.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    authorization_header = (
        f"{algorithm} "
        f"Credential={accessKey}/{credential_scope}, "
        f"SignedHeaders={signed_headers}, "
        f"Signature={signature}"
    )

    headers = {
        "x-amz-date": amz_date,
        "x-amz-security-token": sessionToken,
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
                    raise RequestError()
                return contents
            except ContentTypeError:
                _LOGGER.error(await response.text())
                raise RequestError()
