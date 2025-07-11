import os
import django
import random
import uuid
from faker import Faker
from django.utils import timezone
from django.contrib.auth.hashers import make_password

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
django.setup()

from tournaments.models import (
    Player, Team, TeamMember, Tournament, TournamentParticipant, TournamentMatch,
    TournamentTeam, Squad, SquadMember, News,
    TeamColor, SquadType
)

fake = Faker()

print("Clearing existing data...")
SquadMember.objects.all().delete()
Squad.objects.all().delete()
TournamentTeam.objects.all().delete()
TournamentParticipant.objects.all().delete()
TournamentMatch.objects.all().delete()
Tournament.objects.all().delete()
TeamMember.objects.all().delete()
Team.objects.all().delete()
Player.objects.all().delete()
News.objects.all().delete()

print("Creating players...")
players = []
for _ in range(50):
    players.append(Player.objects.create(
        username=fake.user_name(),
        email=fake.unique.email(),
        password=make_password('password123'),
        is_team_lead=random.choice([True, False]),
        country_code=fake.country_code().lower(),
        points=random.randint(100, 1000),
        kill_death_ratio=round(random.uniform(0.5, 3.5), 2),
        win_rate=round(random.uniform(40, 100), 2)
    ))

def generate_unique_join_code():
    while True:
        code = uuid.uuid4().hex[:10].upper()
        if not Team.objects.filter(join_code=code).exists():
            return code

print("Creating teams...")
teams = []
team_leads = [p for p in players if p.is_team_lead]
random.shuffle(team_leads)
team_names = [
    "Red Devils", "Squad 34", "Vixens", "5 Star Parlays", "OnlyTheOnes", "Faded",
    "Destined XS", "Carolina Jays", "Xarmy", "TakeHomeWinners", "OutNout", "MIL 42s"
]

for i in range(min(4, len(team_leads))):
    lead = team_leads[i]
    team = Team.objects.create(
        name=random.choice(team_names),
        lead_player=lead,
        join_code=generate_unique_join_code()
    )
    teams.append(team)
    TeamMember.objects.create(team=team, player=lead)

    members = {lead}
    while len(members) < 5:
        p = random.choice(players)
        if p not in members:
            TeamMember.objects.create(team=team, player=p)
            members.add(p)

print("Creating tournaments...")
tournaments = []
base_date = timezone.now() + timezone.timedelta(days=1)

for i in range(20):
    start_date = base_date + timezone.timedelta(days=i * 2)
    t = Tournament.objects.create(
        game=random.choice([choice[0] for choice in Tournament.GAME_CHOICES]),
        title=random.choice(["US NORTH INVITATIONALS", "US NORTH GRAND", "EUROPE LEVEL FINALS"]),
        max_players=64,
        registered_players=random.choice([16, 32, 48]),
        mode=random.choice(["16v16", "32v32", "64v64"]),
        region=random.choice([choice[0] for choice in Tournament.REGION_CHOICES]),
        level="BRONZE",
        platform=random.choice([choice[0] for choice in Tournament.PLATFORM_CHOICES]),
        start_date=start_date,
        language="English",
        tournament_type=random.choice(["Elimination", "Round Robin"]),
        bracket_structure={"rounds": random.randint(2, 5)},
        is_active=True
    )
    tournaments.append(t)

tournament = tournaments[0]
print("Registering teams to tournament...")

for i, color in enumerate(TeamColor):
    if i >= len(teams):
        break

    team = teams[i]
    tournament_team = TournamentTeam.objects.create(
        tournament=tournament,
        team=team,
        color=color
    )

    participant = TournamentParticipant.objects.create(
        team=team,
        tournament=tournament
    )

    print(f"Creating squads for {team.name} ({color})...")

    for squad_type in SquadType.choices:
        squad = Squad.objects.create(
            participant=participant,
            squad_type=squad_type[0]
        )

        squad_members = random.sample(list(TeamMember.objects.filter(team=team)), 3)
        roles = ['CAPTAIN', 'LEADER', 'NONE']

        for j, tm in enumerate(squad_members):
            SquadMember.objects.create(
                player=tm.player,
                squad=squad,
                role=roles[j]
            )

print("Creating matches...")
team1, team2 = teams[0], teams[1]

for i in range(10):
    score1 = random.randint(0, 20)
    score2 = random.randint(0, 20)
    winner = team1 if score1 >= score2 else team2

    TournamentMatch.objects.create(
        tournament=tournament,
        round_number=1,
        match_number=i + 1,
        team1=team1,
        team2=team2,
        team1_score=score1,
        team2_score=score2,
        winner=winner,
        mode="TEAM",
        scheduled_time=tournament.start_date
    )

print("Creating news articles...")
for _ in range(10):
    News.objects.create(
        title=fake.catch_phrase(),
        description=fake.paragraph(nb_sentences=4),
        image=fake.image_url(width=640, height=480),
        more_link=fake.url()
    )

print("✅ DONE: Database populated successfully!")