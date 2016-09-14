# Celery

Running add_card and remove_card requires the celery worker to be running.

First make sure you have a redis server running on redis://localhost:6379

Then, run this command in the root directory of the project:

```bash
$ celery -A app.tasks worker
```
