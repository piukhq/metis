# Celery

Running add_card and remove_card requires the celery worker to be running.

First make sure you have a redis server running on redis://localhost:6379

Then, run this command in the root directory of the project:

```bash
$ celery -A app.tasks worker
```

For running the celery worker as a daemon, the following command is sufficient for dev:

```bash
$ /var/.virtualenvs/metis/bin/celery worker -A app.tasks --pidfile=/tmp/celery_metis.pid -D
```

For production environments, something more robust like systemd or supervisord is recommended.

Do Echo test
Set the URL for doEcho testing
MTF: https://ws.mastercard.com/mtf/MRS/DiagnosticService
Prod: https://ws.mastercard.com/MRS/DiagnosticService

In mastercard.py, do_echo_body set the url as follows
        do_echo_url = 'https://ws.mastercard.com/MRS/DiagnosticService'
This is mastercard production URL.

Username and password used in MTF doEcho testing are:
'Yc7xn3gDP73PPOQLEB2BYpv31EV:94iV3Iyvky86avhdjLgIh0z9IFeB0pw4cZvu64ufRgaur46mTM4xepsPDOdxVH51'
Username and password will be different for production and can be obtained from the Bink Environments page on
the Spreedly website.

Set the receiver token to a valid master card Spreedly receiver.
Receiver token used for MTF doEcho: XsXRs91pxREDW7TAFbUc1TgosxU

Set the the payment_method_token with a valid token. Obtained by registering a card with Spreedly.
<payment_method_token>WhtIyJrcpcLupNpBD4bSVx3qyY5</payment_method_token>