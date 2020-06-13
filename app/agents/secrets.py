import requests
import settings


class Secret:

    _values = {}

    file_secrets = {
        "vop_client_certificate_path": {
            "vault_name": "/v1/secret/vop/clientCert",
            "path": "/tmp/vop_client_certificate.pem",
        },
        "vop_client_key_path": {
            "vault_name": "/v1/secret/vop/clientKey",
            "path": "/tmp/vop_client_key.pem",
        }
    }

    attribute_secrets = [

    ]

    @classmethod
    def _azure_request(cls, vault_name):
        azure_vault = "http://127.0.0.1:8200"
        url = f"{azure_vault}{vault_name}"
        return requests.request('GET', url)

    @classmethod
    def load_temp_file_items(cls):
        for secret_name, secret_file_def in cls.file_secrets.items():
            resp = cls._azure_request(secret_file_def['vault_name'])
            resp_dict = resp.json()
            data = resp_dict.get('data', {})
            value = data.get('value', {})
            try:
                with open(secret_file_def['path'], 'w') as file:
                    file.write(value)
            except Exception as err:
                message = f"FAILED {secret_name} was not installed in {secret_file_def['path']} Error: {err}"
                settings.logger.error(message)
            else:
                message = f"Success {secret_name} correctly installed in {secret_file_def['path']}"
                settings.logger.info(message)
                cls._values[secret_name] = secret_file_def['path']

    @classmethod
    def load_from_vault(cls):
        cls.load_temp_file_items()

    @classmethod
    def get(cls, secret_name):
        return cls._values.get(secret_name, 'undefined')

