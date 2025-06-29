from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import TournamentParticipant

@receiver(post_save, sender=TournamentParticipant)
def update_tournament_registration_count(sender, instance, created, **kwargs):
    if created:
        tournament = instance.tournament
        tournament.registered_players = tournament.participants.count()
        tournament.save()