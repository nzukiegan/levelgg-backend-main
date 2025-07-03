# tournaments/services.py
import random
from collections import defaultdict
from typing import List, Dict, Tuple
from .models import Tournament, Team, TournamentParticipant

class SwissPairing:
    def __init__(self, participants: List[TournamentParticipant]):
        self.participants = participants
        self.standings = self._initialize_standings()
    
    def _initialize_standings(self) -> Dict[int, Dict]:
        return {p.id: {
            'participant': p,
            'points': 0,
            'opponents': set(),
            'tiebreakers': defaultdict(int)
        } for p in self.participants}

    def generate_round(self, round_number: int) -> List[Tuple]:
        # Sort by points, then tiebreakers
        sorted_standings = sorted(
            self.standings.values(),
            key=lambda x: (-x['points'], x['tiebreakers']['buchholz'], x['tiebreakers']['solkoff'])
        )
        
        pairings = []
        paired = set()
        
        for i, standing in enumerate(sorted_standings):
            if standing['participant'].id in paired:
                continue
                
            # Find best available opponent
            for j in range(i+1, len(sorted_standings)):
                opponent = sorted_standings[j]
                if (opponent['participant'].id not in paired and 
                    opponent['participant'].id not in standing['opponents']):
                    
                    pairings.append((standing['participant'], opponent['participant']))
                    paired.add(standing['participant'].id)
                    paired.add(opponent['participant'].id)
                    break
        
        return pairings

class SingleEliminationBracket:
    def __init__(self, participants: List[TournamentParticipant]):
        self.participants = participants
    
    def generate_bracket(self) -> Dict:
        num_participants = len(self.participants)
        bracket = {
            'rounds': [],
            'matches': []
        }
        
        # Seed participants
        seeded = sorted(
            self.participants, 
            key=lambda p: p.team.tier, 
            reverse=True
        )
        
        # Create first round matches
        matches = []
        for i in range(0, num_participants, 2):
            if i+1 < num_participants:
                matches.append({
                    'team1': seeded[i].team.id,
                    'team2': seeded[i+1].team.id,
                    'round': 1,
                    'match_num': len(matches) + 1
                })
            else:
                # Handle bye if odd number of teams
                matches.append({
                    'team1': seeded[i].team.id,
                    'team2': None,
                    'round': 1,
                    'match_num': len(matches) + 1,
                    'winner': seeded[i].team.id
                })
        
        bracket['matches'] = matches
        bracket['rounds'] = [{
            'round_num': 1,
            'name': f'Round 1',
            'matches': [m['match_num'] for m in matches]
        }]
        
        return bracket

class DiscordNotifier:
    def __init__(self, client):
        self.client = client
    
    async def notify_player(self, player_id: int, message: str):
        from .models import Player
        try:
            player = Player.objects.get(id=player_id)
            if player.discord_id:
                await self.client.send_direct_message(
                    player.discord_id,
                    message
                )
        except Player.DoesNotExist:
            pass
    
    async def notify_team(self, team_id: int, message: str):
        from .models import TeamMember
        members = TeamMember.objects.filter(team_id=team_id).select_related('player')
        for member in members:
            await self.notify_player(member.player.id, message)