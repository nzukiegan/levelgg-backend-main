from django.contrib import admin
from .models import Player, Team, TeamMember, SocialAccount, Tournament, TournamentParticipant, TournamentMatch, News, TournamentTeam, Squad, SquadMember

@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = ('email', 'username', 'is_team_lead', 'is_admin', 'date_joined', 'country_code', 'points', 'kill_death_ratio', 'win_rate')
    list_filter = ('is_team_lead', 'is_admin')
    search_fields = ('email', 'username')
    ordering = ('-date_joined',)

@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ('name', 'lead_player', 'join_code', 'created_at')
    search_fields = ('name', 'join_code')
    raw_id_fields = ('lead_player',)

@admin.register(TeamMember)
class TeamMemberAdmin(admin.ModelAdmin):
    list_display = ('team', 'player', 'joined_at')
    raw_id_fields = ('team', 'player')

@admin.register(Tournament)
class TournamentAdmin(admin.ModelAdmin):
    list_display = ('title', 'start_date', 'mode', 'region', 'platform', 'is_active')
    list_filter = ('mode', 'region', 'platform', 'is_active')
    search_fields = ('title',)
    date_hierarchy = 'start_date'

@admin.register(TournamentParticipant)
class TournamentParticipantAdmin(admin.ModelAdmin):
    list_display = ('tournament', 'team', 'registered_at')
    raw_id_fields = ('tournament', 'team')

@admin.register(TournamentMatch)
class TournamentMatchAdmin(admin.ModelAdmin):
    list_display = ['tournament', 'round_number', 'match_number', 'team1', 'team2', 'team1_score', 'team2_score', 'winner', 'mode', 'scheduled_time', 'is_completed']
    list_filter = ('tournament', 'is_completed')
    raw_id_fields = ('team1', 'team2', 'winner')

@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
    list_display = ('title', 'date', 'short_description', 'more_link')
    search_fields = ('title', 'description')
    list_filter = ('date',)

    def short_description(self, obj):
        return obj.description[:75] + ('...' if len(obj.description) > 75 else '')
    short_description.short_description = 'Description'


@admin.register(TournamentTeam)
class TournamentTeamAdmin(admin.ModelAdmin):
    list_display = ('tournament', 'team', 'color')
    list_filter = ('color',)
    search_fields = ('team__name', 'tournament__title')

@admin.register(Squad)
class SquadAdmin(admin.ModelAdmin):
    list_display = ('get_tournament', 'get_team', 'squad_type')
    list_filter = ('squad_type',)
    search_fields = (
        'participant__tournament__title',
        'participant__team__name',
    )
    raw_id_fields = ('participant',)

    def get_tournament(self, obj):
        return obj.participant.tournament.title
    get_tournament.short_description = 'Tournament'

    def get_team(self, obj):
        return obj.participant.team.name
    get_team.short_description = 'Team'

@admin.register(SquadMember)
class SquadMemberAdmin(admin.ModelAdmin):
    list_display = (
        'player', 'squad', 'role'
    )
    list_filter = ('role', 'player')
    search_fields = ('player__email', 'player__username')
    raw_id_fields = ('player', 'squad')

@admin.register(SocialAccount)
class SocialAccountAdmin(admin.ModelAdmin):
    list_display = ('user', 'provider', 'uid')
    search_fields = ('user__username', 'provider', 'uid')