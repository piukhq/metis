# Metis

## Production Config

Make sure the `METIS_TESTING` environment variable is set to `False` in production.
This can be set in the `.env` file.

## Celery

Running `add_card` and `remove_card` requires the celery worker to be running.

First make sure you have a redis server running on `redis://localhost:6379`.

Then, run this command in the root directory of the project:

```bash
$ celery -A app.tasks worker
```

For running the celery worker as a daemon, the following command is sufficient for dev:

```bash
$ /var/.virtualenvs/metis/bin/celery worker -A app.tasks --pidfile=/tmp/celery_metis.pid -D
```

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

* MTF: https://ws.mastercard.com/mtf/MRS/DiagnosticService
* Prod: https://ws.mastercard.com/MRS/DiagnosticService

In the `do_echo_body` method in `mastercard.py` set the url as follows:
```python
do_echo_url = 'https://ws.mastercard.com/MRS/DiagnosticService'
```
This is mastercard production URL.

Username and password used in MTF doEcho testing are:
```
Yc7xn3gDP73PPOQLEB2BYpv31EV:94iV3Iyvky86avhdjLgIh0z9IFeB0pw4cZvu64ufRgaur46mTM4xepsPDOdxVH51
```
Username and password will be different for production and can be obtained from the Bink Environments page on
the Spreedly website.

Set the receiver token to a valid master card Spreedly receiver.
Receiver token used for MTF doEcho: `XsXRs91pxREDW7TAFbUc1TgosxU`.

Set the the payment_method_token with a valid token obtained by registering a card with Spreedly.
```
<payment_method_token>WhtIyJrcpcLupNpBD4bSVx3qyY5</payment_method_token>
```
