# Metis

## Production Config

Make sure the `METIS_TESTING` environment variable is set to `False` in production.
This can be set in the `.env` file.

## Celery

Running `add_card` and `remove_card` requires the celery worker to be running.

First make sure you have a RabbitMQ server running on port 5672.

Then, run this command in the root directory of the project, setting concurrency to one for easier debugging

```bash
$ celery -A metis worker --loglevel=INFO --concurrency=1
```

For running the celery worker as a daemon, the following command is sufficient for dev:

```bash
$ /var/.virtualenvs/metis/bin/celery worker -A metis --pidfile=/tmp/celery_metis.pid -D
```
of alternatively set up Pycharm to have a run celery config using the module name celery and
the rest of the command line as parameters.

For production environments, something more robust like systemd or supervisord is recommended.
The `config` directory contains files that can be used to set celery up as a system service.

## RabbitMQ

You can easily run RabbitMQ using the rabbitmq:management image as follows:

```bash
$ docker run -d --hostname rabbitmq --name rabbitmq -p 0.0.0.0:15672:15672 -p 0.0.0.0:5672:5672 rabbitmq:management
```

Navigate to `host-address:15672` in your browser to see the management dashboard. Default login is `guest / guest`.

## Mastercard do-echo test

Set the URL for doEcho testing:

* MTF: https://services.mastercard.com/mtf/MRS/DiagnosticService
* Prod: https://services.mastercard.com/MRS/DiagnosticService

In the `do_echo_body` method in `mastercard.py` set the url as follows:
```python
do_echo_url = 'https://services.mastercard.com/MRS/DiagnosticService'
```
This is mastercard production URL.

Username and password will be different for production and can be obtained from the Bink Environments page on
the Spreedly website.

Set the receiver token to a valid master card Spreedly receiver.
Receiver token used for MTF doEcho: `XsXRs91pxREDW7TAFbUc1TgosxU`.

Set the payment_method_token with a valid token obtained by registering a card with Spreedly.
```
<payment_method_token>WhtIyJrcpcLupNpBD4bSVx3qyY5</payment_method_token>
```
### Secrets and integration testing to Agents.

All secrets are found in the Azure keyvault.  This includes lower security risk secrets used
for integration testing to Agents test services.  Instead of hard coding them or placing in comments
they should be placed in the Dev vault.

It should be noted that doing this gives more control over access to these tokens but because developers
need to use them they may be downloaded into code run locally. They should be discarded after use.
Metis automatically does this by downloading the secrets at the start and apart from VOP client certificates
only keeps them in memory.

Secrets are not required to be downloaded if running with Pelops, this only applies to Integration
testing. Usually developers will work without secrets; for this, the AZURE_VAULT_URL envvar should be a blank string,
and the stubbed amex url should be your local Pelops.

Amex has been updated to align with this policy.  The following config will cause secrets to accessed
on start up and used to talk to Amex Test environment:

        settings.METIS_TESTING = True
        settings.STUBBED_AMEX_URL = "https://api.dev2s.americanexpress.com"
        settings.AZURE_VAULT_URL = "https://bink-uksouth-dev-com.vault.azure.net/"
        vault.secrets_from_vault(start_delay=0)

Note: The above is used in the test SetUp class in Amex integration tests to force the correct config. when running
 the test

Before running the test ensure you have vault access by running:

        brew install azure-cli
        az login

### Environment Variables

- `HERMES_URL`
  - String Value, URL for Hermes
- `METIS_DEBUG`
  - `true` - Enable Application Debug Logging
  - `false` - Disable Application Debug Logging
- `METIS_TESTING`
  - `true` - Use stubbed URLs to talk to Pelops or test Spreedly
  - `false` - Force Production Spreedly environment
- `AZURE_VAULT_URL`
  - String Value, URL from which to fetch secrets. If set to "", local dummy secrets are used for dev purposes.
- `SPREEDLY_BASE_URL`
  - String Value, URL for Spreedly, either `https://core.spreedly.com/v1` or Pelops endpoint
- `SENTRY_DSN`
  - String Value, DSN to Sentry
- `CELERY_BROKER_URL`
  - URL for RabbitMQ/AMQP
