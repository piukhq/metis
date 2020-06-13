import requests
import settings


def _azure_request(vault_name):
    url = f"{settings.AZURE_VAULT_URL}{settings.VAULT_SECRETS_PATH}{vault_name}"
    return requests.request('GET', url)


def _get_secret(vault_name, error_message):
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
            value = None
            message = f"{error_message}: secret may not have been set"
            settings.logger.error(message)
    return value


def _file_items():
    for secret_name, secret_file_def in settings.Secrets.SECRETS_STORED_IN_FILE.items():
        failed_message = f"FAILED {secret_name} was not installed in {secret_file_def['file_path']}"
        secret = _get_secret(secret_file_def['vault_name'], failed_message)

        if secret:
            try:
                with open(secret_file_def['file_path'], 'w') as file:
                    file.write(secret)
            except Exception as err:
                message = f"{failed_message} Exception: {err}"
                settings.logger.error(message)
            else:
                message = f"Success {secret_name} correctly installed in {secret_file_def['file_path']}"
                settings.logger.info(message)
                setattr(settings.Secrets, secret_name, secret_file_def['file_path'])


def _memory_items():
    for secret_name, vault_name in settings.Secrets.SECRETS_STORED_IN_MEMORY.items():
        failed_message = f"FAILED {secret_name} was not set; vault name {vault_name}"
        secret = _get_secret(vault_name, failed_message)
        if secret:
            setattr(settings.Secrets, secret_name, secret)
            message = f"Success {secret_name} set"
            settings.logger.info(message)


def secrets_from_vault():
    _file_items()
    _memory_items()
