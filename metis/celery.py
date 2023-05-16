import celery as c

from metis import settings

celery = c.Celery()
celery.config_from_object(settings)
