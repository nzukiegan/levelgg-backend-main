from django.db import transaction
from django.core.exceptions import ValidationError
from .models import Team, TeamMember

def validate_team_tier(team, player):
    if player.tier != team.tier:
        raise ValidationError(
            f"Player tier ({player.tier}) does not match team tier ({team.tier})"
        )

def create_team_with_lead(team_name, lead_player):
    with transaction.atomic():
        team = Team.objects.create(
            name=team_name,
            lead_player=lead_player,
            tier=lead_player.tier
        )
        TeamMember.objects.create(
            team=team,
            player=lead_player,
            role='CAPTAIN'
        )
    return team

def get_player_teams(player):
    return TeamMember.objects.filter(
        player=player
    ).select_related(
        'team', 'team__lead_player'
    ).order_by('-team__created_at')