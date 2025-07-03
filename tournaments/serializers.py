from rest_framework import serializers
from .models import Player, Team, TeamMember, Tournament, TournamentParticipant, TournamentMatch, News, TournamentTeam, Squad, SquadMember, Player
from django.contrib.auth.hashers import make_password
from django.contrib.auth.password_validation import validate_password

class PlayerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Player
        fields = [
            'id', 'email', 'username', 'is_team_lead',
            'tier', 'skill_rating', 'is_online',
            'discord_id', 'is_admin'
        ]
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def create(self, validated_data):
        validated_data['password'] = make_password(validated_data.get('password'))
        return super().create(validated_data)

class TeamSerializer(serializers.ModelSerializer):
    lead_player = PlayerSerializer(read_only=True)
    join_code = serializers.CharField(read_only=True)

    class Meta:
        model = Team
        fields = [
            'id', 'name', 'created_at',
            'lead_player', 'join_code',
            'is_active', 'tier'
        ]
        read_only_fields = ['created_at', 'lead_player', 'join_code']

class TeamMemberSerializer(serializers.ModelSerializer):
    team = TeamSerializer(read_only=True)
    player = PlayerSerializer(read_only=True)
    team_id = serializers.PrimaryKeyRelatedField(queryset=Team.objects.all(), source='team', write_only=True)
    player_id = serializers.PrimaryKeyRelatedField(queryset=Player.objects.all(), source='player', write_only=True)
    
    class Meta:
        model = TeamMember
        fields = ['id', 'team', 'team_id', 'player', 'role', 'player_id', 'joined_at']

class TournamentSerializer(serializers.ModelSerializer):
    registered_players = serializers.IntegerField(source='participants.count', read_only=True)

    class Meta:
        model = Tournament
        fields = '__all__'

class TournamentParticipantSerializer(serializers.ModelSerializer):
    tournament = TournamentSerializer()
    team = TeamSerializer()
    squads = serializers.SerializerMethodField()

    class Meta:
        model = TournamentParticipant
        fields = ['team', 'id', 'tournament', 'registered_at', 'squads']

    def get_squads(self, obj):
        return SquadSerializer(obj.squads.all().prefetch_related('members__player'), many=True).data


class TournamentMatchSerializer(serializers.ModelSerializer):
    team1 = TeamSerializer(read_only=True)
    team2 = TeamSerializer(read_only=True)
    winner = TeamSerializer(read_only=True)
    team1_id = serializers.PrimaryKeyRelatedField(
        queryset=Team.objects.all(), 
        source='team1', 
        write_only=True, 
        required=False, 
        allow_null=True
    )
    team2_id = serializers.PrimaryKeyRelatedField(
        queryset=Team.objects.all(), 
        source='team2', 
        write_only=True, 
        required=False, 
        allow_null=True
    )
    winner_id = serializers.PrimaryKeyRelatedField(
        queryset=Team.objects.all(), 
        source='winner', 
        write_only=True, 
        required=False, 
        allow_null=True
    )
    
    class Meta:
        model = TournamentMatch
        fields = '__all__'

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password]
    )
    confirm_password = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = Player
        fields = ['email', 'username', 'password', 'confirm_password', 'is_team_lead', 'is_admin']
        extra_kwargs = {
            'is_team_lead': {'write_only': True},
            'is_admin': {'write_only': True},
        }

    def validate(self, attrs):
        if attrs['password'] != attrs['confirm_password']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return attrs

    def create(self, validated_data):
        validated_data.pop('confirm_password')
        user = Player.objects.create_user(
            email=validated_data['email'],
            username=validated_data['username'],
            password=validated_data['password'],
            is_team_lead=validated_data.get('is_team_lead', False),
            is_admin=validated_data.get('is_admin', False)
        )
        return user

class SocialAuthSerializer(serializers.Serializer):
    provider = serializers.CharField(max_length=20)
    access_token = serializers.CharField()
    
    def validate_provider(self, value):
        valid_providers = ['discord', 'twitch', 'facebook']
        if value not in valid_providers:
            raise serializers.ValidationError('Unsupported provider')
        return value

class TournamentSerializer(serializers.ModelSerializer):
    game = serializers.SerializerMethodField()
    
    class Meta:
        model = Tournament
        fields = [
            'id',
            'title',
            'start_date',
            'mode',
            'region',
            'platform',
            'language',
            'registered_players',
            'max_players',
            'is_active',
            'game'
        ]
    
    def get_game(self, obj):
        return obj.game


class LoginAuthSerializer(serializers.Serializer):
    provider = serializers.ChoiceField(choices=['discord', 'twitch', 'facebook'])
    code = serializers.CharField(required=True)

class SignUpAuthSerializer(serializers.Serializer):
    provider = serializers.ChoiceField(choices=['discord', 'twitch', 'facebook'])
    access_token = serializers.CharField(required=True)

class NewsSerializer(serializers.ModelSerializer):
    class Meta:
        model = News
        fields = '__all__'

class SquadMemberSerializer(serializers.ModelSerializer):
    player_id = serializers.IntegerField(source='player.id', read_only=True)
    player_name = serializers.CharField(source='player.username', read_only=True)
    player_email = serializers.CharField(source='player.email', read_only=True)
    is_online = serializers.BooleanField(source='player.is_online', read_only=True)
    
    rank = serializers.CharField(read_only=True)
    country = serializers.CharField(read_only=True)
    points = serializers.IntegerField(read_only=True)
    kd = serializers.FloatField(source='kill_death_ratio', read_only=True)
    winrate = serializers.FloatField(source='win_rate', read_only=True)
    role = serializers.CharField(read_only=True)
    action_role = serializers.CharField(read_only=True)

    icon = serializers.SerializerMethodField()
    country_icon = serializers.SerializerMethodField()

    class Meta:
        model = SquadMember
        fields = [
            'id',
            'player_id', 'player_name', 'player_email', 'is_online',
            'icon', 'rank', 'country', 'country_icon',
            'points', 'kd', 'winrate', 'role', 'action_role'
        ]

    def get_icon(self, obj):
        return f"/players/{obj.player.username.lower()}.png" if obj.player.username else "/players/default.png"

    def get_country_icon(self, obj):
        if obj.country:
            country_code = obj.country.lower()
            return f"/flags/{country_code}.png"
        return None


class SquadSerializer(serializers.ModelSerializer):
    members = SquadMemberSerializer(many=True, read_only=True)
    icon = serializers.SerializerMethodField()
    tournament_name = serializers.SerializerMethodField()
    team_name = serializers.SerializerMethodField()

    class Meta:
        model = Squad
        fields = [
            'id', 'squad_type', 'members', 'participant',
            'tournament_name', 'team_name', 'icon'
        ]
    
    def get_icon(self, obj):
        icon_map = {
            'INFANTRY': '/infantry2.png',
            'ARMOR': '/armor2.png',
            'HELI': '/heli.png',
            'JET': '/jet.png',
        }
        return icon_map.get(obj.squad_type, '/icons/default.png')

    def get_tournament_name(self, obj):
        return obj.participant.tournament.title if obj.participant and obj.participant.tournament else None

    def get_team_name(self, obj):
        return obj.participant.team.name if obj.participant and obj.participant.team else None


class TournamentTeamSerializer(serializers.ModelSerializer):
    squads = SquadSerializer(many=True, read_only=True)
    tournament_id = serializers.IntegerField(source='tournament.id')
    tournament_title = serializers.CharField(source='tournament.title')
    team_id = serializers.IntegerField(source='team.id')
    team_name = serializers.CharField(source='team.name')
    team_tier = serializers.CharField(source='team.tier')

    class Meta:
        model = TournamentTeam
        fields = [
            'id', 'color', 'squads', 'tournament_id', 'tournament_title',
            'team_id', 'team_name', 'team_tier'
        ]

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['squads'] = sorted(
            representation['squads'],
            key=lambda x: ['INFANTRY', 'ARMOR', 'HELI', 'JET'].index(x['squad_type'])
        )
        return representation


class TeamSquadManagementSerializer(serializers.ModelSerializer):
    tournament_teams = serializers.SerializerMethodField()
    members = serializers.SerializerMethodField()

    class Meta:
        model = Team
        fields = ['id', 'name', 'tier', 'tournament_teams', 'members']

    def get_tournament_teams(self, obj):
        teams = TournamentTeam.objects.filter(team=obj).select_related(
            'tournament', 'team'
        ).prefetch_related('squads__members__player')
        return TournamentTeamSerializer(teams, many=True).data

    def get_members(self, obj):
        from .team_serializers import TeamMemberSerializer
        return TeamMemberSerializer(obj.members.all(), many=True).data

class TournamentParticipantTeamSerializer(serializers.ModelSerializer):
    team_name = serializers.SerializerMethodField()
    squads = serializers.SerializerMethodField()

    class Meta:
        model = TournamentParticipant
        fields = ['team_name', 'squads']

    def get_team_name(self, obj):
        return obj.team.name

    def get_squads(self, obj):
        return SquadSerializer(obj.squads.all(), many=True).data


class TournamentDetailSerializer(serializers.ModelSerializer):
    teams = TournamentParticipantTeamSerializer(source='participants', many=True)

    class Meta:
        model = Tournament
        fields = ['title', 'max_players', 'registered_players', 'start_date', 'mode', 'region', 'platform', 'language', 'level', 'teams']

class MatchSerializer(serializers.ModelSerializer):
    teamA = serializers.SerializerMethodField()
    teamB = serializers.SerializerMethodField()
    winner = serializers.SerializerMethodField()
    bgImg = serializers.SerializerMethodField()
    mode = serializers.SerializerMethodField()
    players = serializers.SerializerMethodField()
    zone = serializers.SerializerMethodField()
    score = serializers.SerializerMethodField()
    formatted_date = serializers.SerializerMethodField()

    class Meta:
        model = TournamentMatch
        fields = [
            'id', 'teamA', 'teamB', 'winner', 'bgImg',
            'mode', 'players', 'zone', 'score', 'formatted_date'
        ]

    def get_teamA(self, obj):
        return obj.team1.name if obj.team1 else "TBD"

    def get_teamB(self, obj):
        return obj.team2.name if obj.team2 else "TBD"

    def get_winner(self, obj):
        if obj.winner == obj.team1:
            return "A"
        elif obj.winner == obj.team2:
            return "B"
        return None

    def get_bgImg(self, obj):
        return "/match-bg.jpg"

    def get_mode(self, obj):
        return obj.mode if obj.mode else obj.tournament.mode

    def get_players(self, obj):
        half = obj.tournament.max_players // 2 if obj.tournament else 0
        return f"{half} v {half}"

    def get_zone(self, obj):
        half = obj.tournament.max_players // 2 if obj.tournament else 0
        return f"USA NORTH - {half} v {half}"

    def get_score(self, obj):
        return f"{obj.team1_score} - {obj.team2_score}"

    def get_formatted_date(self, obj):
        return obj.scheduled_time.strftime("%b %d, %Y") if obj.scheduled_time else "TBD"

class TournamentTeamSerializer(serializers.ModelSerializer):
    team_name = serializers.CharField(source='team.name', read_only=True)
    tournament_name = serializers.CharField(source='tournament.title', read_only=True)

    class Meta:
        model = TournamentTeam
        fields = ['id', 'team', 'tournament', 'color', 'team_name', 'tournament_name']

class RegisteredTournamentSerializer(serializers.ModelSerializer):
    tournament = TournamentSerializer()
    team = serializers.SerializerMethodField()

    class Meta:
        model = TournamentParticipant
        fields = ['id', 'tournament', 'team', 'registered_at']

    def get_team(self, obj):
        return {
            'id': obj.team.id,
            'name': obj.team.name
        }

class AllTeamDetailsSerializer(serializers.ModelSerializer):
    squad_type = serializers.CharField()
    has_squad_lead = serializers.SerializerMethodField()

    class Meta:
        model = Squad
        fields = ['id', 'squad_type', 'has_squad_lead']

    def get_has_squad_lead(self, obj):
        return SquadMember.objects.filter(squad=obj, role='LEADER').exists()