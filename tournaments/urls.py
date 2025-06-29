from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    PlayerViewSet, TeamViewSet, TeamMemberViewSet,
    TournamentViewSet, TournamentParticipantViewSet, TournamentMatchViewSet, member_stats, LoginView, TournamentListView, RegistrationView, SocialSignupView, SocialCallbackView, SocialLoginView, NewsListView, UpcomingTournamentView, MatchListView
)

router = DefaultRouter()
router.register(r'players', PlayerViewSet)
router.register(r'teams', TeamViewSet)
router.register(r'team-members', TeamMemberViewSet)
router.register(r'tournaments', TournamentViewSet)
router.register(r'tournament-participants', TournamentParticipantViewSet)
router.register(r'tournament-matches', TournamentMatchViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('member-stats/', member_stats, name='member-stats'),
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/social/login/', SocialLoginView.as_view(), name='social-login'),
    path('auth/register/', RegistrationView.as_view(), name='register'),
    path('auth/social/signup/', SocialSignupView.as_view(), name='social-signup'),
    path('upcoming_tournaments/', TournamentListView.as_view(), name='tournament-list'),
    path('upcoming_tournament/', UpcomingTournamentView.as_view(), name='upcoming-tournaments'), #this is for teams
    path('matches/', MatchListView.as_view(), name='matches-list'),
    path('news/', NewsListView.as_view(), name='news-list'),
]