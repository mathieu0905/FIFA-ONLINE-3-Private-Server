"""Build computer match squads at +10/LV30 without changing stored rosters."""
import copy
import functools

VERSION = 'ai-opponents-grade10-level30-v1'
GRADE = 10
LEVEL = 30


def install(host):
    if getattr(host, '_ai_opponent_progression_installed', False):
        return
    if host.MAX_GRADE < GRADE or host.PLAYER_MAX_LEVEL < LEVEL:
        raise RuntimeError('AI progression requires existing +10 and LV30 support')
    original = host.match_side

    @functools.wraps(original)
    def match_side(raw, teamid, user=None, tactics=None):
        if user is None:
            raw = copy.deepcopy(raw)
            for player in raw['players']:
                player['grade'] = GRADE
                player['levelinfo'] = {'level': LEVEL, 'exp': 0}
        return original(raw, teamid, user, tactics)

    def rules(query, body):
        return host._json(dict(version=VERSION, grade=GRADE, level=LEVEL,
                               applies_to='computer-controlled match sides',
                               stored_rosters_changed=False))

    host.match_side = match_side
    host.ENDPOINTS['/info/ai-opponent-rules'] = rules
    host._ai_opponent_progression_installed = True
