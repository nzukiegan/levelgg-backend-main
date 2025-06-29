from django.utils import timezone
from .models import Player
from django.conf import settings

class OnlineStatusMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.online_threshold = getattr(settings, 'ONLINE_THRESHOLD_MINUTES', 5)

    def __call__(self, request):
        response = self.get_response(request)
        
        if request.user.is_authenticated:
            ip_address = self.get_client_ip(request)
            Player.objects.filter(pk=request.user.pk).update(
                last_activity=timezone.now(),
                last_login_ip=ip_address
            )
            self.update_online_status(request.user)
            
        return response
    
    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        return x_forwarded_for.split(',')[0] if x_forwarded_for else request.META.get('REMOTE_ADDR')
    
    def update_online_status(self, user):
        now = timezone.now()
        threshold = now - timezone.timedelta(minutes=self.online_threshold)
        was_online = user.is_online
        is_now_online = user.last_activity >= threshold
        
        if was_online != is_now_online:
            Player.objects.filter(pk=user.pk).update(is_online=is_now_online)