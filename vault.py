import requests
import settings
from time import sleep
from copy import deepcopy


def _azure_request(vault_name):
    url = f"{settings.AZURE_VAULT_URL}{settings.VAULT_SECRETS_PATH}{vault_name}"
    return requests.request('GET', url)


def _get_secret(vault_name, error_message):
    value = None
    try:
        resp = _azure_request(vault_name)
        resp_dict = resp.json()
    except Exception as err:
        message = f"{error_message} Bad vault response invalid JSON Exception: {err}"
        settings.logger.error(message)
    else:
        if resp_dict:
            data = resp_dict.get('data', {})
            value = data.get('value', None)
        if not value:
            message = f"{error_message}"
            settings.logger.error(message)
    return value


def _save_secret_to_file(secret_name, secret, file_path, failed_message):
    ok = False
    try:
        with open(file_path, 'w') as file:
            file.write(secret)
    except Exception as err:
        message = f"{failed_message} Exception: {err}"
        settings.logger.error(message)
    else:
        message = f"Success {secret_name} correctly installed in {file_path}"
        settings.logger.info(message)
        ok = True
        setattr(settings.Secrets, secret_name, file_path)
    return ok


def _items(secret_name, secret_def):
    failed_message = f"FAILED to set {secret_name} from vault: {secret_def['vault_name']}"
    secret = _get_secret(secret_def['vault_name'], failed_message)
    file_path = secret_def.get('file_path', None)
    ok = False
    if secret:
        if file_path:
            failed_message = f"{failed_message} while trying to save to {secret_def['file_path']}"
            ok = _save_secret_to_file(secret_name, secret, file_path, failed_message)
        else:
            setattr(settings.Secrets, secret_name, secret)
            message = f"Success {secret_name} set"
            settings.logger.info(message)
            ok = True
    return ok


def secrets_from_vault():
    secrets = deepcopy(settings.Secrets.SECRETS_DEF)
    time_delay = 10
    while secrets:
        sleep(time_delay)
        try_items = deepcopy(secrets)
        for secret_name, secret_def in try_items.items():
            ok = _items(secret_name, secret_def)
            if ok:
                del(secrets[secret_name])
        time_delay = 5
