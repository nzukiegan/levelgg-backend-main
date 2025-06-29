from celery import shared_task
from django.utils import timezone
from .models import Player

@shared_task
def update_online_statuses():
    from django.conf import settings
    threshold = timezone.now() - timezone.timedelta(
        minutes=settings.ONLINE_THRESHOLD_MINUTES
    )
    
    Player.objects.filter(
        is_online=True,
        last_activity__lt=threshold
    ).update(is_online=False)
    
    Player.objects.filter(
        is_online=False,
        last_activity__gte=threshold
    ).update(is_online=True)