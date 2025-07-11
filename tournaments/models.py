from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission
import uuid
import json

class Player(AbstractUser):
    TIER_CHOICES = [
        ('BRONZE', 'Bronze'),
        ('SILVER', 'Silver'),
        ('GOLD', 'Gold'),
        ('PLATINUM', 'Platinum'),
        ('DIAMOND', 'Diamond'),
    ]
    RANK_CHOICES = [
        ('RECRUIT', 'Recruit'),
        ('PRIVATE', 'Private'),
        ('CORPORAL', 'Corporal'),
        ('SERGEANT', 'Sergeant'),
        ('STAFF_SERGEANT', 'Staff Sergeant'),
        ('SERGEANT_MAJOR', 'Sergeant Major'),
        ('LIEUTENANT', 'Lieutenant'),
        ('CAPTAIN', 'Captain'),
        ('MAJOR', 'Major'),
        ('COLONEL', 'Colonel'),
        ('GENERAL', 'General'),
    ]

    is_team_lead = models.BooleanField(default=False)
    is_team_captain = models.BooleanField(default=False)
    is_admin = models.BooleanField(default=False)
    email = models.EmailField(unique=True)
    is_online = models.BooleanField(default=False)
    last_activity = models.DateTimeField(auto_now=True)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    tier = models.CharField(max_length=20, choices=TIER_CHOICES, default='BRONZE')

    skill_rating = models.IntegerField(default=1000)
    preferred_roles = models.JSONField(default=list)
    discord_id = models.CharField(max_length=100, blank=True, null=True)

    country_code = models.CharField(max_length=2, blank=True, null=True)
    points = models.IntegerField(default=0)
    kill_death_ratio = models.FloatField(default=0.0)
    win_rate = models.FloatField(default=0.0) 
    rank = models.CharField(max_length=30, choices=RANK_CHOICES, default='Private')

    class Meta:
        db_table = 'tournaments_player'

    groups = models.ManyToManyField(
        Group,
        related_name='player_groups',
        blank=True,
    )

    user_permissions = models.ManyToManyField(
        Permission,
        related_name='player_permissions',
        blank=True,
    )
    
    def update_activity(self, ip_address=None):
        self.last_activity = timezone.now()
        if ip_address:
            self.last_login_ip = ip_address
        self.save(update_fields=['last_activity', 'last_login_ip'])
        self.update_online_status()
    
    def update_online_status(self, threshold_minutes=5):
        now = timezone.now()
        time_delta = now - self.last_activity
        is_now_online = time_delta.total_seconds() < threshold_minutes * 60
        
        if self.is_online != is_now_online:
            self.is_online = is_now_online
            self.save(update_fields=['is_online'])
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
    def __str__(self):
        return self.email

class Team(models.Model):
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    lead_player = models.OneToOneField(Player, on_delete=models.CASCADE, related_name='led_team')
    join_code = models.CharField(max_length=10, unique=True, default=uuid.uuid4().hex[:10].upper())
    is_active = models.BooleanField(default=True)
    tier = models.CharField(max_length=20, choices=Player.TIER_CHOICES, default='BRONZE')
    
    def save(self, *args, **kwargs):
        if not self.pk and not self.tier:
            self.tier = self.lead_player.tier
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class TeamMember(models.Model):
    ROLE_CHOICES = [
        ('MEMBER', 'Member'),
        ('CO_LEAD', 'Co-Lead'),
        ('CAPTAIN', 'Captain'),
    ]
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='members')
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='teams')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='MEMBER')
    joined_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('team', 'player')
    
    def __str__(self):
        return f"{self.player.email} in {self.team.name}"

class Tournament(models.Model):
    BRACKET_TYPES = [
        ('SINGLE_ELIM', 'Single Elimination'),
        ('DOUBLE_ELIM', 'Double Elimination'),
        ('SWISS', 'Swiss'),
        ('ROUND_ROBIN', 'Round Robin')
    ]

    MODE_CHOICES = [
        ('16v16', '16v16'),
        ('32v32', '32v32'),
        ('64v64', '64v64'),
    ]
    
    REGION_CHOICES = [
        ('NA', 'North America'),
        ('EU', 'Europe'),
        ('ASIA', 'Asia'),
        ('OCE', 'Oceania'),
        ('GLOBAL', 'Global'),
    ]
    
    LEVEL_CHOICES = [
        ('BRONZE', 'Bronze'),
        ('SILVER', 'Silver'),
        ('GOLD', 'Gold'),
        ('PLATINUM', 'Platinum'),
        ('DIAMOND', 'Diamond')
    ]
    
    PLATFORM_CHOICES = [
        ('PC', 'PC'),
        ('CONSOLE', 'Console'),
        ('MOBILE', 'Mobile'),
        ('CROSS', 'Cross-Platform'),
    ]

    GAME_CHOICES = [
        ('BATTLEFIELD', 'Battlefield'),
        ('NHL', 'NHL'),
        ('OTHER', 'Other'),
    ]
    
    game = models.CharField(
        max_length=20,
        choices=GAME_CHOICES,
        default='BATTLEFIELD'
    )
    
    title = models.CharField(max_length=255)
    max_players = models.IntegerField()
    registered_players = models.IntegerField(default=0)
    mode = models.CharField(max_length=10, choices=MODE_CHOICES)
    region = models.CharField(max_length=10, choices=REGION_CHOICES)
    level = models.CharField(max_length=15, choices=LEVEL_CHOICES)
    platform = models.CharField(max_length=10, choices=PLATFORM_CHOICES)
    start_date = models.DateTimeField()
    language = models.CharField(max_length=100)
    tournament_type = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    bracket_structure = models.JSONField(default=dict)
    bracket_type = models.CharField(max_length=20, choices=BRACKET_TYPES, default='SINGLE_ELIM')
    is_started = models.BooleanField(default=False)
    is_completed = models.BooleanField(default=False)
    current_round = models.IntegerField(default=0)

    def generate_bracket(self):
        if self.bracket_type == 'SWISS':
            return self._generate_swiss_bracket()
        elif self.bracket_type == 'SINGLE_ELIM':
            return self._generate_single_elim_bracket()

    def _generate_swiss_bracket(self):
        from .services import SwissPairing
        participants = list(self.participants.all().select_related('team'))
        return SwissPairing(participants).generate_round(self.current_round)

    def _generate_single_elim_bracket(self):
        from .services import SingleEliminationBracket
        participants = list(self.participants.all().select_related('team'))
        return SingleEliminationBracket(participants).generate_bracket()

    def get_squad_limits(self):
        limits = {
            '16v16': (2, 4),
            '32v32': (6, 8),
            '64v64': (8, 12),
        }
        return limits.get(self.mode, (0, 0))
    
    def can_create_more_squads(self, participant):
        min_squads, max_squads = self.get_squad_limits()
        if max_squads == 0:
            return False
        
        existing_squads = Squad.objects.filter(
            participant=participant
        ).count()
        
        return existing_squads < max_squads

    def __str__(self):
        return self.title

class TournamentParticipant(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='tournaments')
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, related_name='participants')
    registered_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('team', 'tournament')
    
    def __str__(self):
        return f"{self.team.name} in {self.tournament.title}"

class TournamentMatch(models.Model):
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, related_name='matches')
    round_number = models.IntegerField()
    match_number = models.IntegerField()
    team1 = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, blank=True, related_name='team1_matches')
    team2 = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, blank=True, related_name='team2_matches')
    winner = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, blank=True, related_name='won_matches')
    
    team1_score = models.IntegerField(default=0)
    team2_score = models.IntegerField(default=0)

    mode = models.CharField(max_length=30, choices=Tournament.MODE_CHOICES, blank=True)

    is_completed = models.BooleanField(default=False)
    scheduled_time = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('tournament', 'round_number', 'match_number')

    def __str__(self):
        return f"Match {self.match_number} (Round {self.round_number}) in {self.tournament.title}"


class SocialToken(models.Model):
    player = models.OneToOneField(Player, on_delete=models.CASCADE, related_name='social_token')
    provider = models.CharField(max_length=30)
    uid = models.CharField(max_length=100, unique=True)
    access_token = models.TextField()
    expires_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.provider} token for {self.player.email}"

class SocialAccount(models.Model):
    user = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='tournament_social_accounts')
    provider = models.CharField(max_length=30)
    uid = models.CharField(max_length=100, unique=True)
    extra_data = models.JSONField(default=dict)

    class Meta:
        db_table = 'social_account'


class News(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    image = models.URLField()
    date = models.DateField(auto_now_add=True)
    more_link = models.URLField()

    class Meta:
        db_table = 'news'

    def __str__(self):
        return self.title

class TeamColor(models.TextChoices):
    RED = 'RED', 'Red'
    BLUE = 'BLUE', 'Blue'

class PlayerRole(models.TextChoices):
    CAPTAIN = 'CAPTAIN', 'Captain'
    SQUAD_LEADER = 'SQUAD_LEADER', 'Squad Leader'
    MEMBER = 'MEMBER', 'Member'

class TournamentTeam(models.Model):
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, related_name='tournament_teams')
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    color = models.CharField(max_length=10, choices=TeamColor.choices)

    class Meta:
        unique_together = ('tournament', 'color')

    def __str__(self):
        return f"{self.color} - {self.team.name} in {self.tournament.title}"


class SquadType(models.TextChoices):
    ALPHA = 'ALPHA', 'Alpha'
    BRAVO = 'BRAVO', 'Bravo'
    CHARLIE = 'CHARLIE', 'Charlie'
    DELTA = 'DELTA', 'Delta'
    ECHO = 'ECHO', 'Echo'
    FOXTROT = 'FOXTROT', 'Foxtrot'
    GOLF = 'GOLF', 'Golf'
    HOTEL = 'HOTEL', 'Hotel'
    INDIA = 'INDIA', 'India'
    JULIET = 'JULIET', 'Juliet'

class Squad(models.Model):
    participant = models.ForeignKey(
        'TournamentParticipant',
        on_delete=models.CASCADE,
        related_name='squads',
        null=True,
    )
    squad_type = models.CharField(
        max_length=15,
        choices=SquadType.choices
    )

    class Meta:
        unique_together = ('participant', 'squad_type')
        verbose_name = 'Squad'
        verbose_name_plural = 'Squads'

    def __str__(self):
        return f"{self.participant.team.name} - {self.squad_type} Squad in {self.participant.tournament.title}"

class SquadMember(models.Model):
    ROLE_CHOICES = [
        ('CAPTAIN', 'Team Captain'),
        ('LEADER', 'Squad Leader'),
        ('NONE', 'No Role'),
    ]

    ACTION_ROLE_CHOICES = [
        ('INFANTRY', 'Infantry'),
        ('ARMOR', 'Armor'),
        ('HELI', 'Heli'),
        ('JET', 'Jet'),
    ]

    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='squad_memberships')
    squad = models.ForeignKey(Squad, on_delete=models.CASCADE, related_name='members')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='NONE')
    action_role = models.CharField(max_length=10, choices=ACTION_ROLE_CHOICES, default='INFANTRY')

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['squad'], condition=models.Q(role='CAPTAIN'), name='unique_captain_per_squad'),
            models.UniqueConstraint(fields=['squad'], condition=models.Q(role='LEADER'), name='unique_leader_per_squad'),
        ]

    def __str__(self):
        return f"{self.player.email} in {self.squad} - {self.role}"