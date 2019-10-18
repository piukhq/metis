import celery as c
import settings

celery = c.Celery()
celery.config_from_object(settings)
