from django.test import TestCase
from django.contrib.auth import get_user_model
from .models import Team, Tournament, TournamentParticipant, TournamentMatch

User = get_user_model()

class TournamentModelTests(TestCase):
    def setUp(self):
        self.player1 = User.objects.create_user(
            email='player1@test.com',
            username='player1',
            password='testpass123',
            is_team_lead=True
        )
        self.player2 = User.objects.create_user(
            email='player2@test.com',
            username='player2',
            password='testpass123'
        )
        self.team = Team.objects.create(
            name='Test Team',
            lead_player=self.player1,
            join_code='TEST123'
        )
        self.tournament = Tournament.objects.create(
            title='Test Tournament',
            max_players=16,
            mode='TEAM',
            region='NA',
            level='INTERMEDIATE',
            platform='PC',
            start_date='2023-12-31T00:00:00Z',
            language='English',
            tournament_type='Single Elimination'
        )

    def test_team_creation(self):
        self.assertEqual(self.team.name, 'Test Team')
        self.assertEqual(self.team.lead_player.email, 'player1@test.com')
        self.assertTrue(self.team.join_code)

    def test_tournament_creation(self):
        self.assertEqual(self.tournament.title, 'Test Tournament')
        self.assertEqual(self.tournament.mode, 'TEAM')
        self.assertEqual(self.tournament.registered_players, 0)

    def test_tournament_registration(self):
        participant = TournamentParticipant.objects.create(
            tournament=self.tournament,
            team=self.team
        )
        self.tournament.refresh_from_db()
        self.assertEqual(self.tournament.registered_players, 1)
        self.assertEqual(participant.team.name, 'Test Team')

    def test_match_creation(self):
        match = TournamentMatch.objects.create(
            tournament=self.tournament,
            round_number=1,
            match_number=1,
            team1=self.team
        )
        self.assertEqual(match.tournament.title, 'Test Tournament')
        self.assertFalse(match.is_completed)

class TournamentViewTests(TestCase):
    pass