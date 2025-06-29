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
    TournamentTeam, Squad, SquadMember, News
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
    player = Player.objects.create(
        username=fake.user_name(),
        email=fake.unique.email(),
        password=make_password('password123'),
        is_team_lead=random.choice([True, False]),
    )
    players.append(player)

def generate_unique_join_code():
    while True:
        code = uuid.uuid4().hex[:10].upper()
        if not Team.objects.filter(join_code=code).exists():
            return code

print("Creating teams...")
teams = []
for i in range(4):
    lead = random.choice(players)
    team = Team.objects.create(
        name = random.choice(["Red Devils", "Squad 34", "Vixens", "5 Star Parlays", "OnlyTheOnes", "Faded", "Destined XS", "Carolina Jays", "Xarmy", "TakeHomeWinners", "OutNout", "MIL 42s"]),
        lead_player=lead,
        join_code=generate_unique_join_code()
    )
    teams.append(team)
    TeamMember.objects.create(team=team, player=lead)

    members = set([lead])
    while len(members) < 5:
        p = random.choice(players)
        if p not in members:
            TeamMember.objects.create(team=team, player=p)
            members.add(p)

tournaments = []
base_date = timezone.now() + timezone.timedelta(days=1)

for i in range(20):
    start_date = base_date + timezone.timedelta(days=i * 2)

    t = Tournament.objects.create(
        game=random.choice(["BATTLEFIELD", "NHL"]),
        title=random.choice(["US NORTH INVITATIONALS", "US NORTH GRAND", "EUROPE LEVEL FINALS"]),
        max_players=64,
        registered_players=random.choice([16, 32, 48]),
        mode="TEAM",
        region=random.choice(["US NORTH", "EUROPE"]),
        level=random.choice(["BEGINNER", "INTERMEDIATE", "ADVANCED"]),
        platform=random.choice(["PC", "Console"]),
        start_date=start_date,
        language="English",
        tournament_type=random.choice(["Elimination", "Round Robin"]),
        bracket_structure={"rounds": random.randint(2, 5)},
        is_active=True
    )
    tournaments.append(t)

tournament = tournaments[0]

print("Registering RED and BLUE teams...")
colors = ['RED', 'BLUE']
for i in range(2):
    team = teams[i]
    tournament_team = TournamentTeam.objects.create(
        tournament=tournament,
        team=team,
        color=colors[i]
    )
    TournamentParticipant.objects.create(team=team, tournament=tournament)

    print(f"Creating squads for {team.name} ({colors[i]})...")
    for squad_type in ['INFANTRY', 'ARMOR', 'HELI', 'JET']:
        squad = Squad.objects.create(
            tournament_team=tournament_team,
            squad_type=squad_type
        )

        squad_members = random.sample(list(TeamMember.objects.filter(team=team)), 3)
        roles = ['CAPTAIN', 'LEADER', 'NONE']
        for j, tm in enumerate(squad_members):
            SquadMember.objects.create(
                player=tm.player,
                squad=squad,
                role=roles[j],
                rank=random.choice(["Sergeant", "Corporal", "Lieutenant", "Major"]),
                country=fake.country_code().lower(),
                points=random.randint(100, 1000),
                kill_death_ratio=round(random.uniform(0.5, 3.5), 2),
                win_rate=round(random.uniform(40, 100), 2)
            )


print("Creating multiple tournament matches with scores and mode...")
team1 = teams[0]
team2 = teams[1]

for i in range(10):
    team1_score = random.randint(0, 20)
    team2_score = random.randint(0, 20)
    winner_team = team1 if team1_score >= team2_score else team2

    TournamentMatch.objects.create(
        tournament=tournament,
        round_number=1,
        match_number=i + 1,
        team1=team1,
        team2=team2,
        team1_score=team1_score,
        team2_score=team2_score,
        winner=winner_team,
        mode=random.choice(["CONQUEST", "DOMINATION", "FLAG CUPTURE"]),
        scheduled_time=tournament.start_date
    )

print("Creating news...")
for _ in range(10):
    News.objects.create(
        title=fake.catch_phrase(),
        description=fake.paragraph(nb_sentences=4),
        image=fake.image_url(width=640, height=480),
        more_link=fake.url()
    )

print("✅ DONE: Database populated successfully!")