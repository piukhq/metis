import json
from copy import deepcopy
from time import sleep
from typing import Optional

from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

import settings


class SecretError(Exception):
    """Exception raised for errors in secret fetching/setting."""

    def __init__(self, message: Optional[str] = None) -> None:
        self.message = message

    def __str__(self) -> str:
        return f"Secrets Error: {self.message}"


def _get_secret_value(client, vault_name):
    secret = client.get_secret(vault_name).value
    return json.loads(secret)["value"]


def _save_secret_to_file(secret_name, secret, file_path):
    with open(file_path, "w") as file:
        file.write(secret)
    settings.logger.info(f"Success {secret_name} correctly installed in {file_path}")
    setattr(settings.Secrets, secret_name, file_path)
    return True


def fetch_and_set_secret(client: SecretClient, secret_name: str, secret_def: dict) -> None:
    secret_value = _get_secret_value(client, secret_def["vault_name"])
    file_path = secret_def.get("file_path", None)

    if file_path:
        _save_secret_to_file(secret_name, secret_value, file_path)
        setattr(settings.Secrets, secret_name, file_path)
    else:
        setattr(settings.Secrets, secret_name, secret_value)


def secrets_from_vault(start_delay=10, loop_delay=5, max_retries=5):

    secrets_to_fetch = deepcopy(settings.Secrets.SECRETS_DEF)

    time_delay = start_delay
    loops = 0

    client = get_azure_client()

    while secrets_to_fetch:
        sleep(time_delay)
        to_load = deepcopy(secrets_to_fetch)

        for secret_name, secret_def in to_load.items():
            try:
                fetch_and_set_secret(client, secret_name, secret_def)
                del secrets_to_fetch[secret_name]
                settings.logger.info(f"Successfully set secret: {secret_name}")
            except Exception as e:
                settings.logger.error(f"Error fetching and setting {secret_name} from Vault. {e}")

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
