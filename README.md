# Celery

Running add_card and remove_card requires the celery worker to be running.

Run this command in the root directory of the project:

```shell
celery -A app.tasks worker```
