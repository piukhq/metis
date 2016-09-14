from celery import Celery
import settings

celery = Celery()
celery.config_from_object(settings)
