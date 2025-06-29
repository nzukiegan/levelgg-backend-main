from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from rest_framework.decorators import action, api_view
from django.contrib.auth import get_user_model, authenticate
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.timezone import now
from django.http import JsonResponse
from django.conf import settings
from django.contrib.auth.models import BaseUserManager
from rest_framework_simplejwt.tokens import RefreshToken
from datetime import timedelta
from .models import Player, SocialToken
import random
import string
import os
import requests
from django.db import models
from .models import Player, Team, TeamMember, Tournament, TournamentParticipant, TournamentMatch, SocialAccount, News
from .serializers import (
    PlayerSerializer, TeamSerializer, TeamMemberSerializer,
    TournamentSerializer, TournamentParticipantSerializer, TournamentMatchSerializer,
    UserRegistrationSerializer, LoginAuthSerializer, NewsSerializer, SignUpAuthSerializer, TournamentDetailSerializer, MatchSerializer
)
from django.db import transaction
from rest_framework import generics

User = get_user_model()

class PlayerViewSet(viewsets.ModelViewSet):
    queryset = Player.objects.all()
    serializer_class = PlayerSerializer

    def get_permissions(self):
        if self.action in ['create']:
            return []
        elif self.action in ['update', 'partial_update', 'destroy']:
            return [IsAdminUser()]
        return [IsAuthenticated()]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class LoginView(APIView):
    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')

        user = authenticate(email=email, password=password)
        if user:
            refresh = RefreshToken.for_user(user)
            return Response({
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user': PlayerSerializer(user).data
            }, status=status.HTTP_200_OK)

        return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

class SocialLoginView(APIView):
    def post(self, request):
        serializer = LoginAuthSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            provider = serializer.validated_data['provider']
            code = serializer.validated_data['code']

            if provider == 'discord':
                access_token = self.get_discord_access_token(code)
                user_info = self.verify_discord_token(access_token)
            elif provider == 'twitch':
                access_token = self.get_twitch_access_token(code)
                user_info = self.verify_twitch_token(access_token)
            elif provider == 'facebook':
                access_token = self.get_facebook_access_token(code)
                user_info = self.verify_facebook_token(access_token)
            else:
                return Response({'error': 'Unsupported provider'}, status=status.HTTP_400_BAD_REQUEST)

            uid = user_info['id']
            social_account = SocialAccount.objects.get(provider=provider, uid=uid)
            user = social_account.user
            refresh = RefreshToken.for_user(user)

            return Response({
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                },
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'username': user.username,
                    'is_admin': user.is_admin,
                    'is_team_lead': user.is_team_lead
                }
            }, status=status.HTTP_200_OK)

        except SocialAccount.DoesNotExist:
            return Response({'error': 'not_registered'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def get_discord_access_token(self, code):
        discord_app = settings.SOCIALACCOUNT_PROVIDERS['discord']['APP']
        
        data = {
            'client_id': discord_app['client_id'],
            'client_secret': discord_app['secret'],
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': 'http://localhost:3000/login_callback?provider=discord',
        }

        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        response = requests.post('https://discord.com/api/oauth2/token', data=data, headers=headers)
        response.raise_for_status()
        return response.json()['access_token']

    def get_twitch_access_token(self, code):
        twitch_app = settings.SOCIALACCOUNT_PROVIDERS['twitch']['APP']

        data = {
            'client_id': twitch_app['client_id'],
            'client_secret': twitch_app['secret'],
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': 'http://localhost:3000/login_callback?provider=twitch',  # or set via .env
        }

        response = requests.post('https://id.twitch.tv/oauth2/token', data=data)
        response.raise_for_status()
        return response.json()['access_token']


    def get_facebook_access_token(self, code):
        facebook_app = settings.SOCIALACCOUNT_PROVIDERS['facebook']['APP']

        params = {
            'client_id': facebook_app['client_id'],
            'client_secret': facebook_app['secret'],
            'redirect_uri': 'http://localhost:3000/login_callback?provider=facebook',  # or set via .env
            'code': code
        }

        response = requests.get('https://graph.facebook.com/v19.0/oauth/access_token', params=params)
        response.raise_for_status()
        return response.json()['access_token']

    def verify_discord_token(self, access_token):
        headers = {'Authorization': f'Bearer {access_token}'}
        response = requests.get('https://discord.com/api/users/@me', headers=headers)
        response.raise_for_status()
        return response.json()

    def verify_twitch_token(self, access_token):
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Client-Id': settings.TWITCH_CLIENT_ID
        }
        response = requests.get('https://api.twitch.tv/helix/users', headers=headers)
        response.raise_for_status()
        return response.json().get('data', [{}])[0]

    def verify_facebook_token(self, access_token):
        params = {'access_token': access_token, 'fields': 'id,name,email'}
        response = requests.get('https://graph.facebook.com/me', params=params)
        response.raise_for_status()
        return response.json()

class RegistrationView(APIView):
    def post(self, request):
        email = request.data.get('email')
        username = request.data.get('username')
        password = request.data.get('password')
        confirm_password = request.data.get('confirm_password')

        if not all([email, username, password, confirm_password]):
            return Response({"detail": "All fields are required."}, status=status.HTTP_400_BAD_REQUEST)

        if password != confirm_password:
            return Response({"detail": "Passwords do not match."}, status=status.HTTP_400_BAD_REQUEST)

        if Player.objects.filter(email=email).exists():
            return Response(
                {"detail": "An account with this email already exists. Please log in instead."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if Player.objects.filter(username=username).exists():
            return Response(
                {"detail": "An account with this username already exists."},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = Player.objects.create_user(email=email, username=username, password=password)
        refresh = RefreshToken.for_user(user)

        return Response({
            "message": "Registration successful.",
            "user": {
                "id": user.id,
                "email": user.email,
                "username": user.username,
            },
            "tokens": {
                "refresh": str(refresh),
                "access": str(refresh.access_token),
            }
        }, status=status.HTTP_201_CREATED)


class SocialSignupView(APIView):
    def post(self, request):
        try:
            print(request.data)
            serializer = SignUpAuthSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            provider = serializer.validated_data['provider']
            access_token = serializer.validated_data['access_token']
            if provider == 'discord':
                user_info = self.verify_discord_token(access_token)
            elif provider == 'twitch':
                user_info = self.verify_twitch_token(access_token)
            elif provider == 'facebook':
                user_info = self.verify_facebook_token(access_token)
            else:
                return Response({'error': 'Unsupported provider'}, status=status.HTTP_400_BAD_REQUEST)

            social_account, user = self.get_or_create_social_account(provider, user_info, access_token)

            print("Social account created")

            refresh = RefreshToken.for_user(user)

            print("Successfuly retrieved refresh token")

            return Response({
                'message': 'Social authentication successful',
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                },
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                }
            }, status=status.HTTP_200_OK)
        except ValidationError as ve:
            return Response(
                {"detail": str(ve)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            print("Unexpected error:", str(e))
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def verify_discord_token(self, access_token):
        headers = {'Authorization': f'Bearer {access_token}'}
        response = requests.get('https://discord.com/api/users/@me', headers=headers)
        if response.status_code != 200:
            raise ValueError('Invalid Discord access token')
        return response.json()

    def verify_twitch_token(self, access_token):
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Client-Id': settings.SOCIALACCOUNT_PROVIDERS['twitch']['APP']['client_id']
        }
        response = requests.get('https://api.twitch.tv/helix/users', headers=headers)
        if response.status_code != 200:
            raise ValueError('Invalid Twitch access token')
        return response.json().get('data', [{}])[0]

    def verify_facebook_token(self, access_token):
        params = {'access_token': access_token, 'fields': 'id,name,email'}
        response = requests.get('https://graph.facebook.com/me', params=params)
        if response.status_code != 200:
            raise ValueError('Invalid Facebook access token')
        return response.json()

    def get_or_create_social_account(self, provider, user_info, access_token):
        uid = user_info['id']
        try:
            social_account = SocialAccount.objects.get(provider=provider, uid=uid)
            user = social_account.user
            print("Social account exists")
        except SocialAccount.DoesNotExist:
            print("Social account doesn not exist")
            email = user_info.get('email', f'{uid}@{provider}.fake')
            username = user_info.get('username') or user_info.get('name') or provider + '_' + uid[:6]

            if Player.objects.filter(email=email).exists():
                raise ValidationError("An account with this email already exists. Please log in instead.")

            user = Player.objects.create_user(
                email=email,
                username=username,
                password=self.make_random_password()
            )

            print("User created successfuly")

            social_account = SocialAccount.objects.create(
                provider=provider,
                uid=uid,
                extra_data=user_info,
                user=user
            )

            print("SOcial account created successfuly")

        SocialToken.objects.update_or_create(
            player=user,
            provider=provider,
            defaults={
                'uid': uid,
                'access_token': access_token,
                'expires_at': timezone.now() + timedelta(days=30)
            }
        )

        return social_account, user

    def make_random_password(self, length=12):
        chars = string.ascii_letters + string.digits + string.punctuation
        return ''.join(random.SystemRandom().choice(chars) for _ in range(length))


class NewsListView(APIView):
    def get(self, request):
        news = News.objects.order_by('-date')[:10]
        serializer = NewsSerializer(news, many=True)
        return Response(serializer.data)

class SocialCallbackView(APIView):
    def get(self, request):
        access_token = request.GET.get('access_token')
        provider = request.GET.get('provider')

        if not access_token or not provider:
            return Response({'error': 'Missing access token or provider'}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "provider": provider,
            "access_token": access_token,
        })

class TeamViewSet(viewsets.ModelViewSet):
    queryset = Team.objects.all()
    serializer_class = TeamSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        if self.request.user.is_admin:
            return self.queryset
        return self.queryset.filter(lead_player=self.request.user)
    
    def perform_create(self, serializer):
        if not self.request.user.is_team_lead:
            raise serializers.ValidationError("Only team leads can create teams")
        
        join_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        while Team.objects.filter(join_code=join_code).exists():
            join_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        
        serializer.save(lead_player=self.request.user, join_code=join_code)
    
    @action(detail=True, methods=['post'])
    def join(self, request, pk=None):
        team = self.get_object()
        join_code = request.data.get('join_code', '')
        
        if team.join_code != join_code:
            return Response({'error': 'Invalid join code'}, status=status.HTTP_400_BAD_REQUEST)
        
        if TeamMember.objects.filter(team=team, player=request.user).exists():
            return Response({'error': 'Already a member of this team'}, status=status.HTTP_400_BAD_REQUEST)
        
        TeamMember.objects.create(team=team, player=request.user)
        return Response({'success': 'Joined team successfully'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['get'])
    def members(self, request, pk=None):
        team = self.get_object()
        members = TeamMember.objects.filter(team=team)
        serializer = TeamMemberSerializer(members, many=True)
        return Response(serializer.data)

class TeamMemberViewSet(viewsets.ModelViewSet):
    queryset = TeamMember.objects.all()
    serializer_class = TeamMemberSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        if self.request.user.is_admin:
            return self.queryset
        return self.queryset.filter(team__lead_player=self.request.user)
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.team.lead_player != request.user and not request.user.is_admin:
            return Response(
                {'error': 'Only team lead or admin can remove members'},
                status=status.HTTP_403_FORBIDDEN
            )
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

class TournamentViewSet(viewsets.ModelViewSet):
    queryset = Tournament.objects.all()
    serializer_class = TournamentSerializer
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [IsAuthenticated()]
        return [IsAdminUser()]
    
    @action(detail=True, methods=['post'])
    def register(self, request, pk=None):
        tournament = self.get_object()
        team_id = request.data.get('team_id')
        
        if not team_id:
            return Response({'error': 'team_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            team = Team.objects.get(id=team_id, lead_player=request.user)
        except Team.DoesNotExist:
            return Response({'error': 'Team not found or you are not the lead'}, status=status.HTTP_404_NOT_FOUND)
        
        if TournamentParticipant.objects.filter(tournament=tournament, team=team).exists():
            return Response({'error': 'Team already registered'}, status=status.HTTP_400_BAD_REQUEST)
        
        if tournament.participants.count() >= tournament.max_players:
            return Response({'error': 'Tournament is full'}, status=status.HTTP_400_BAD_REQUEST)
        
        participant = TournamentParticipant.objects.create(tournament=tournament, team=team)
        tournament.registered_players += 1
        tournament.save()
        
        serializer = TournamentParticipantSerializer(participant)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def generate_bracket(self, request, pk=None):
        tournament = self.get_object()
        
        if not request.user.is_admin:
            return Response(
                {'error': 'Only admins can generate brackets'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        participants = list(tournament.participants.all())
        if not participants:
            return Response({'error': 'No participants registered'}, status=status.HTTP_400_BAD_REQUEST)
        
        TournamentMatch.objects.filter(tournament=tournament).delete()
        
        num_teams = len(participants)
        num_rounds = (num_teams - 1).bit_length()
        
        bracket = {}
        matches = []
        
        first_round_teams = participants.copy()
        random.shuffle(first_round_teams)
        
        first_round_matches = []
        match_num = 1
        
        for i in range(0, len(first_round_teams), 2):
            if i+1 < len(first_round_teams):
                match = TournamentMatch(
                    tournament=tournament,
                    round_number=1,
                    match_number=match_num,
                    team1=first_round_teams[i].team,
                    team2=first_round_teams[i+1].team
                )
                matches.append(match)
                first_round_matches.append(match)
                match_num += 1
            else:
                match = TournamentMatch(
                    tournament=tournament,
                    round_number=1,
                    match_number=match_num,
                    team1=first_round_teams[i].team,
                    is_completed=True,
                    winner=first_round_teams[i].team
                )
                matches.append(match)
                first_round_matches.append(match)
                match_num += 1
        
        current_round_matches = first_round_matches
        for round_num in range(2, num_rounds + 1):
            next_round_matches = []
            match_num = 1
            
            for i in range(0, len(current_round_matches), 2):
                if i+1 < len(current_round_matches):
                    match = TournamentMatch(
                        tournament=tournament,
                        round_number=round_num,
                        match_number=match_num
                    )
                    matches.append(match)
                    next_round_matches.append(match)
                    match_num += 1
                else:
                    pass
            
            current_round_matches = next_round_matches
        
        final_match = TournamentMatch(
            tournament=tournament,
            round_number=num_rounds + 1,
            match_number=1
        )
        matches.append(final_match)
        
        TournamentMatch.objects.bulk_create(matches)
        
        return Response({'success': 'Bracket generated successfully'}, status=status.HTTP_200_OK)

class TournamentParticipantViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = TournamentParticipant.objects.all()
    serializer_class = TournamentParticipantSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        if self.request.user.is_admin:
            return self.queryset
        return self.queryset.filter(team__lead_player=self.request.user)

class TournamentMatchViewSet(viewsets.ModelViewSet):
    queryset = TournamentMatch.objects.all()
    serializer_class = TournamentMatchSerializer
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [IsAuthenticated()]
        return [IsAdminUser()]
    
    def get_queryset(self):
        tournament_id = self.request.query_params.get('tournament_id')
        if tournament_id:
            return self.queryset.filter(tournament_id=tournament_id)
        return self.queryset
    
    @action(detail=True, methods=['post'])
    def set_winner(self, request, pk=None):
        match = self.get_object()
        winner_id = request.data.get('winner_id')
        
        if not request.user.is_admin:
            return Response(
                {'error': 'Only admins can set match winners'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if not winner_id:
            return Response({'error': 'winner_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            winner = Team.objects.get(id=winner_id)
        except Team.DoesNotExist:
            return Response({'error': 'Team not found'}, status=status.HTTP_404_NOT_FOUND)
        
        if winner not in [match.team1, match.team2]:
            return Response(
                {'error': 'Winner must be one of the competing teams'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        match.winner = winner
        match.is_completed = True
        match.save()
        
        next_round = match.round_number + 1
        next_match_number = (match.match_number + 1) // 2
        
        try:
            next_match = TournamentMatch.objects.get(
                tournament=match.tournament,
                round_number=next_round,
                match_number=next_match_number
            )
            
            if match.match_number % 2 == 1:
                next_match.team1 = winner
            else:
                next_match.team2 = winner
            
            next_match.save()
        except TournamentMatch.DoesNotExist:
            pass
        
        return Response({'success': 'Winner set successfully'}, status=status.HTTP_200_OK)

@api_view(['GET'])
def member_stats(request):
    total_members = Player.objects.count()
    
    threshold = timezone.now() - timezone.timedelta(minutes=5)
    online_members = Player.objects.filter(
        last_activity__gte=threshold
    ).count()
    
    today = timezone.now().date()
    active_today = Player.objects.filter(
        last_activity__date=today
    ).count()
    
    return Response({
        'total_members': total_members,
        'online_members': online_members,
        'active_today': active_today,
        'last_updated': timezone.now().isoformat()
    })

class MemberStatsView(APIView):
    def get(self, request):
        total_members = Player.objects.count()
        online_members = Player.objects.filter(is_online=True).count()
        
        return Response({
            'total_members': total_members,
            'online_members': online_members
        })

class TournamentListView(generics.ListAPIView):
    serializer_class = TournamentSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        all_tournaments = Tournament.objects.all()

        upcoming = Tournament.objects.filter(
            is_active=True,
            start_date__gt=timezone.now()
        ).order_by('start_date')

        return upcoming
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'tournaments': serializer.data,
            'count': queryset.count()
        })


class UpcomingTournamentView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        tournament = Tournament.objects.filter(start_date__gte=now(), is_active=True).order_by('start_date').first()
        if not tournament:
            return Response({"error": "No upcoming tournament found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = TournamentDetailSerializer(tournament)
        return Response(serializer.data, status=status.HTTP_200_OK)

class MatchListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        matches = TournamentMatch.objects.select_related(
            'tournament', 'team1', 'team2', 'winner'
        ).filter(tournament__is_active=True).order_by('-scheduled_time')[:20]

        serializer = MatchSerializer(matches, many=True)
        return Response(serializer.data)