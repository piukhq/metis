import json
from copy import deepcopy
from pathlib import Path
from time import sleep

from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from loguru import logger

from metis.settings import settings


class Secrets:
    # These attributes will contain the secrets
    vop_client_certificate_path: str = ""
    vop_client_key_path: str = ""
    spreedly_visa_receive_token: str = ""
    spreedly_amex_receive_token: str = ""
    spreedly_mastercard_receive_token: str = ""
    vop_user_id: str = ""
    vop_password: str = ""
    spreedly_vop_user_id: str = ""
    spreedly_vop_password: str = ""
    vop_community_code: str = ""
    vop_spreedly_community_code: str = ""
    vop_merchant_group: str = ""
    vop_offer_id: str = ""
    amex_client_id: str = ""
    amex_client_secret: str = ""
    spreedly_oauth_username: str = ""
    spreedly_oauth_password: str = ""

    # One entry for each of the above attributes is required for app to start  The secret is stored in the attribute
    # unless file path is declared in which case the secret is saved to the file and the attribute set to the file path
    SECRETS_DEF = {
        "vop_client_certificate_path": {
            "vault_name": "vop-clientCert",
            "file_path": "/tmp/vop_client_certificate.pem",
        },
        "vop_client_key_path": {
            "vault_name": "vop-clientKey",
            "file_path": "/tmp/vop_client_key.pem",
        },
        "spreedly_visa_receive_token": {"vault_name": "spreedly-visaReceiveToken"},
        "spreedly_amex_receive_token": {"vault_name": "spreedly-amexReceiveToken"},
        "spreedly_mastercard_receive_token": {"vault_name": "spreedly-mastercardReceiveToken"},
        "vop_community_code": {"vault_name": "vop-communityCode"},
        "vop_spreedly_community_code": {"vault_name": "vop-spreedlyCommunityCode"},
        "vop_offer_id": {"vault_name": "vop-offerId"},
        "vop_user_id": {"vault_name": "vop-authUserId"},
        "vop_password": {"vault_name": "vop-authPassword"},
        "spreedly_vop_user_id": {"vault_name": "spreedly-vopAuthUserId"},
        "spreedly_vop_password": {"vault_name": "spreedly-vopAuthPassword"},
        "vop_merchant_group": {"vault_name": "vop-merchantGroup"},
        "amex_client_id": {"vault_name": "amex-clientId"},
        "amex_client_secret": {"vault_name": "amex-clientSecret"},
        "spreedly_oauth_username": {"vault_name": "spreedly-oAuthUsername"},
        "spreedly_oauth_password": {"vault_name": "spreedly-oAuthPassword"},
    }


class SecretError(Exception):
    """Exception raised for errors in secret fetching/setting."""

    def __init__(self, message: str | None = None) -> None:
        self.message = message

    def __str__(self) -> str:
        return f"Secrets Error: {self.message}"


def _get_secret_value(client: SecretClient, vault_name: str) -> str:
    if secret := client.get_secret(vault_name).value:
        return json.loads(secret)["value"]

    raise ValueError(f"could not fetch secret {vault_name} from vault")


def _save_secret_to_file(secret_name: str, secret: str, file_path: str) -> bool:
    Path(file_path).write_text(secret)
    logger.info("Success {} correctly installed in {}", secret_name, file_path)
    setattr(Secrets, secret_name, file_path)
    return True


def fetch_and_set_secret(client: SecretClient, secret_name: str, secret_def: dict) -> None:
    secret_value = _get_secret_value(client, secret_def["vault_name"])
    file_path = secret_def.get("file_path", None)

    if file_path:
        _save_secret_to_file(secret_name, secret_value, file_path)
        setattr(Secrets, secret_name, file_path)
    else:
        setattr(Secrets, secret_name, secret_value)


def secrets_from_vault(start_delay: int = 10, loop_delay: int = 5, max_retries: int = 5) -> None:
    secrets_to_load = deepcopy(Secrets.SECRETS_DEF)

    time_delay = start_delay
    loops = 0

    client = get_azure_client()

    while secrets_to_load:
        sleep(time_delay)

        secrets_loaded = []

        for secret_name, secret_def in secrets_to_load.items():
            try:
                fetch_and_set_secret(client, secret_name, secret_def)
                secrets_loaded.append(secret_name)
                logger.info("Successfully set secret: {}", secret_name)
            except Exception as e:
                logger.error("Error fetching and setting {} from Vault. {}", secret_name, e)

        for secret_name in secrets_loaded:
            del secrets_to_load[secret_name]

        time_delay = loop_delay
        loops += 1

        if loops == max_retries:
            raise SecretError("Max retries reached whilst trying to fetch and set secrets")


def get_azure_client() -> SecretClient:
    azure_credential = DefaultAzureCredential(
        exclude_environment_credential=True,
        exclude_shared_token_cache_credential=True,
        exclude_visual_studio_code_credential=True,
        exclude_interactive_browser_credential=True,
    )

    client = SecretClient(vault_url=settings.AZURE_VAULT_URL, credential=azure_credential)

    return client


if settings.AZURE_VAULT_URL:
    secrets_from_vault()
else:
    Secrets.vop_client_certificate_path = ""
    Secrets.vop_client_key_path = ""
    Secrets.spreedly_visa_receive_token = "visa"
    Secrets.spreedly_amex_receive_token = "amex"
    Secrets.spreedly_mastercard_receive_token = "mastercard"
    Secrets.vop_user_id = "test"
    Secrets.vop_password = "test"
    Secrets.spreedly_vop_user_id = "test"
    Secrets.spreedly_vop_password = "test"
    Secrets.vop_community_code = "community_code"
    Secrets.vop_spreedly_community_code = "spreedly_code"
    Secrets.vop_merchant_group = "test_merch"
    Secrets.vop_offer_id = "12345"
    Secrets.amex_client_id = "test"
    Secrets.amex_client_secret = "test"
    Secrets.spreedly_oauth_username = "test"
    Secrets.spreedly_oauth_password = "test"
