from rest_framework import serializers
from .models import Player, Team, TeamMember, Tournament, TournamentParticipant, TournamentMatch, News, TournamentTeam, Squad, SquadMember, Player
from django.contrib.auth.hashers import make_password
from django.contrib.auth.password_validation import validate_password

class PlayerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Player
        fields = ['id', 'email', 'username', 'is_team_lead', 'is_admin']
        extra_kwargs = {'password': {'write_only': True}}
    
    def create(self, validated_data):
        validated_data['password'] = make_password(validated_data.get('password'))
        return super().create(validated_data)

class TeamSerializer(serializers.ModelSerializer):
    lead_player = PlayerSerializer(read_only=True)
    lead_player_id = serializers.PrimaryKeyRelatedField(
        queryset=Player.objects.filter(is_team_lead=True), 
        source='lead_player', 
        write_only=True
    )
    
    class Meta:
        model = Team
        fields = ['id', 'name', 'created_at', 'lead_player', 'lead_player_id', 'join_code', 'is_active']

class TeamMemberSerializer(serializers.ModelSerializer):
    team = TeamSerializer(read_only=True)
    player = PlayerSerializer(read_only=True)
    team_id = serializers.PrimaryKeyRelatedField(queryset=Team.objects.all(), source='team', write_only=True)
    player_id = serializers.PrimaryKeyRelatedField(queryset=Player.objects.all(), source='player', write_only=True)
    
    class Meta:
        model = TeamMember
        fields = ['id', 'team', 'team_id', 'player', 'player_id', 'joined_at']

class TournamentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tournament
        fields = '__all__'

class TournamentParticipantSerializer(serializers.ModelSerializer):
    color = serializers.SerializerMethodField()
    squads = serializers.SerializerMethodField()

    class Meta:
        model = TournamentParticipant
        fields = ['team', 'color', 'squads']

    def get_color(self, obj):
        try:
            tt = TournamentTeam.objects.get(team=obj.team, tournament=obj.tournament)
            return tt.color
        except TournamentTeam.DoesNotExist:
            return None

    def get_squads(self, obj):
        try:
            tt = TournamentTeam.objects.get(team=obj.team, tournament=obj.tournament)
            return SquadSerializer(tt.squads.all(), many=True).data
        except TournamentTeam.DoesNotExist:
            return []

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
    player_name = serializers.CharField(source='player.username')
    rank = serializers.CharField()
    country = serializers.CharField()
    points = serializers.IntegerField()
    kd = serializers.FloatField(source='kill_death_ratio')
    winrate = serializers.FloatField(source='win_rate')
    icon = serializers.SerializerMethodField()
    country_icon = serializers.SerializerMethodField()

    class Meta:
        model = SquadMember
        fields = ['player_name', 'icon', 'rank', 'country', 'country_icon', 'points', 'kd', 'winrate']

    def get_icon(self, obj):
        return "/player.png"

    def get_country_icon(self, obj):
        return f"/flags/{obj.country.lower()}.png"


class SquadSerializer(serializers.ModelSerializer):
    members = SquadMemberSerializer(many=True)

    class Meta:
        model = Squad
        fields = ['squad_type', 'members']
    
    def get_icon(self, obj):
        icon_map = {
            'INFANTRY': '/infantry2.png',
            'ARMOR': '/armor2.png',
            'HELI': '/heli.png',
            'JET': '/jet.png',
        }
        return icon_map.get(obj.squad_type, '/icons/default.png')


class TournamentTeamSerializer(serializers.ModelSerializer):
    squads = SquadSerializer(many=True)
    color = serializers.SerializerMethodField()

    class Meta:
        model = TournamentTeam
        fields = ['color', 'squads']

    def get_color(self, obj):
        try:
            tournament_team = TournamentTeam.objects.get(team=obj.team, tournament=obj.tournament)
            return tournament_team.color
        except TournamentTeam.DoesNotExist:
            return None

    def get_squads(self, obj):
        try:
            tournament_team = TournamentTeam.objects.get(team=obj.team, tournament=obj.tournament)
            return SquadSerializer(tournament_team.squads.all(), many=True).data
        except TournamentTeam.DoesNotExist:
            return []

class TournamentParticipantTeamSerializer(serializers.ModelSerializer):
    color = serializers.SerializerMethodField()
    squads = serializers.SerializerMethodField()

    class Meta:
        model = TournamentParticipant
        fields = ['team', 'color', 'squads']

    def get_color(self, obj):
        try:
            tt = TournamentTeam.objects.get(team=obj.team, tournament=obj.tournament)
            return tt.color
        except TournamentTeam.DoesNotExist:
            return None

    def get_squads(self, obj):
        try:
            tt = TournamentTeam.objects.get(team=obj.team, tournament=obj.tournament)
            return SquadSerializer(tt.squads.all(), many=True).data
        except TournamentTeam.DoesNotExist:
            return []

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