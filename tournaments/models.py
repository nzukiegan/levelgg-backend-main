from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission
import uuid
import json

class Player(AbstractUser):
    is_team_lead = models.BooleanField(default=False)
    is_admin = models.BooleanField(default=False)
    email = models.EmailField(unique=True)
    is_online = models.BooleanField(default=False)
    last_activity = models.DateTimeField(auto_now=True)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)

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
    lead_player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='led_teams')
    join_code = models.CharField(max_length=10, unique=True, default=uuid.uuid4().hex[:10].upper())
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name

class TeamMember(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='members')
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='teams')
    joined_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('team', 'player')
    
    def __str__(self):
        return f"{self.player.email} in {self.team.name}"

class Tournament(models.Model):
    MODE_CHOICES = [
        ('SOLO', 'Solo'),
        ('TEAM', 'Team'),
    ]
    
    REGION_CHOICES = [
        ('NA', 'North America'),
        ('EU', 'Europe'),
        ('ASIA', 'Asia'),
        ('OCE', 'Oceania'),
        ('GLOBAL', 'Global'),
    ]
    
    LEVEL_CHOICES = [
        ('BEGINNER', 'Beginner'),
        ('INTERMEDIATE', 'Intermediate'),
        ('ADVANCED', 'Advanced'),
        ('PRO', 'Professional'),
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

class SquadType(models.TextChoices):
    INFANTRY = 'INFANTRY', 'Infantry'
    ARMOR = 'ARMOR', 'Armor'
    HELI = 'HELI', 'Heli'
    JET = 'JET', 'Jet'

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
    INFANTRY = 'INFANTRY', 'Infantry'
    ARMOR = 'ARMOR', 'Armor'
    HELI = 'HELI', 'Heli'
    JET = 'JET', 'Jet'

class Squad(models.Model):
    tournament_team = models.ForeignKey(
        'TournamentTeam',
        on_delete=models.CASCADE,
        related_name='squads'
    )
    squad_type = models.CharField(
        max_length=15,
        choices=SquadType.choices
    )

    class Meta:
        unique_together = ('tournament_team', 'squad_type')
        verbose_name = 'Squad'
        verbose_name_plural = 'Squads'

    def __str__(self):
        return f"{self.tournament_team} - {self.squad_type} Squad"

class SquadMember(models.Model):
    ROLE_CHOICES = [
        ('CAPTAIN', 'Team Captain'),
        ('LEADER', 'Squad Leader'),
        ('NONE', 'No Role'),
    ]

    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='squad_memberships')
    squad = models.ForeignKey(Squad, on_delete=models.CASCADE, related_name='members')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='NONE')

    rank = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    points = models.IntegerField(default=0)
    kill_death_ratio = models.FloatField(default=0.0)
    win_rate = models.FloatField(default=0.0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['squad'], condition=models.Q(role='CAPTAIN'), name='unique_captain_per_squad'),
            models.UniqueConstraint(fields=['squad'], condition=models.Q(role='LEADER'), name='unique_leader_per_squad'),
        ]

    def __str__(self):
        return f"{self.player.email} in {self.squad} - {self.role}"
