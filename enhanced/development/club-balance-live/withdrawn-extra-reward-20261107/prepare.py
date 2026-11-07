"""Minimal delta on the fresh official source; no service hooks or formal writes."""
from pathlib import Path
import ast
import hashlib
import importlib.util
import json
import sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parent
SERVER=Path('D:/FO3ID/server')
CLIENT=Path('D:/FO3ID/32795')


def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module
    spec.loader.exec_module(module)
    return module


def write(path,obj):
    Path(path).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf8')


def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def replace_once(source,old,new):
    if source.count(old)!=1:raise RuntimeError('Fresh source changed; review delta: '+old[:120])
    return source.replace(old,new)


def transform(source):
    if 'TC_ORDINARY_CLUB_BASE' in source:raise RuntimeError('Ordinary club support already installed')
    source=replace_once(source,
        'TC_CLUB_GROUPS = _tc_groups((4, 5, 1), (6, 7, 2), (8, 9, 3), (10, 11, 4))',
        'TC_CLUB_GROUPS = _tc_groups((4, 5, 1), (6, 7, 3), (8, 9, 5), (10, 10, 7), (11, 11, 8))')
    source=replace_once(source,
        'TC_LEGENDS = (93, 30, 27, 71, 51, 61, 89, 48, 55, 49, 327)  # WL UL EL ML TL VL CL MUL MUA TCO92',
        '''TC_LEGENDS = (93, 30, 27, 71, 51, 61, 89, 48, 55, 49, 327)  # WL UL EL ML TL VL CL MUL MUA TCO92
# Ordinary-season support is a separate native feature color, exclusive by card
# season. ICON, nostalgia, every existing ordinary legend, moments and future
# fantasy cards do not count or receive it. WB and ordinary annual/UCL cards do.
TC_ORDINARY_CLUB_BASE = 1000000
TC_ORDINARY_EXCLUDED_SEASONS = frozenset(TC_LEGENDS + (12, 19, 26, 31, 32, 33, 37, 38, 39, 41, 43, 84, 95, 97, 327))
TC_ORDINARY_CLUB_GROUPS = _tc_groups((3, 4, 1), (5, 6, 2), (7, 8, 3), (9, 11, 4))''')
    source=replace_once(source,
        '@functools.lru_cache(maxsize=None)\ndef tc_special_sets():',
        '''@functools.lru_cache(maxsize=None)
def tc_ordinary_club_names():
    """Installed localized team identities; no synthesized or guessed club IDs."""
    with open(os.path.join(HERE, "server_display_zh.json"), encoding="utf-8") as stream:
        return json.load(stream)["names_by_id"]["TEAMNAMES_CHI.json"]


@functools.lru_cache(maxsize=None)
def tc_ordinary_club_sets():
    """Static ordinary-card memberships for real clubs, shared across all seasons.

    Current clubs need an actual domestic league; history clubs use the verified
    playerhistory records. National teams and all-star/fantasy placeholder teams
    cannot become a shortcut to the ordinary club reward. Runtime counts still
    use the XI's distinct identities through active_teamcolors.
    """
    cards, history = tc_static()
    labels = tc_ordinary_club_names()
    with closing(_db()) as connection:
        nations = {row[0] for row in connection.execute("SELECT DISTINCT nationalteamid FROM players")}
        current_clubs = {row[0] for row in connection.execute(
            "SELECT DISTINCT teamid FROM players WHERE leagueid NOT IN (78, 2028, 9998, 9999)")}
        placeholder_clubs = {row[0] for row in connection.execute(
            "SELECT DISTINCT teamid FROM players WHERE leagueid IN (2028, 9998, 9999)")} - current_clubs
    known_clubs = current_clubs | {club for clubs in history.values() for club in clubs}
    known_clubs = {club for club in known_clubs if 0 < club < 900000 and club not in nations and club not in placeholder_clubs and str(club) in labels}
    members, identities = {}, {}
    for spid, (playerid, club, _) in cards.items():
        if spid < 1000000 or spid // 1000000 in TC_ORDINARY_EXCLUDED_SEASONS:
            continue
        for teamid in ({club} | history.get(playerid, set())) & known_clubs:
            cid = TC_ORDINARY_CLUB_BASE + teamid
            members.setdefault(cid, set()).add(spid)
            identities.setdefault(cid, set()).add(playerid)
    return {cid: (frozenset(spids), len(identities[cid])) for cid, spids in sorted(members.items()) if len(identities[cid]) >= 3}


@functools.lru_cache(maxsize=None)
def tc_special_sets():''')
    source=replace_once(source,
        '    return {cid: (frozenset(s for s, _ in got), len({p for _, p in got})) for cid, got in sets.items()}',
        '''    result = {cid: (frozenset(s for s, _ in got), len({p for _, p in got})) for cid, got in sets.items()}
    ordinary = tc_ordinary_club_sets()
    if result.keys() & ordinary.keys():
        raise ValueError("Ordinary club feature ID collides with an existing color")
    result.update(ordinary)
    return result''')
    source=replace_once(source,
        '    return [club, nation] + grades + clubs + nations + specials + [moments]',
        '''    labels = tc_ordinary_club_names()
    ordinary = [{"teamcolorid": cid, "type": "feature", "teamid": str(cid),
                 "name": labels[str(cid - TC_ORDINARY_CLUB_BASE)] + "·普通赛季额外奖励",
                 "description": "同队普通赛季首发3–4人+1、5–6人+2、7–8人+3、9–11人+4；仅合资格普通赛季卡享有，与队套及强化套叠加，同人不重复计数、多队户口取最高奖励",
                 "boostgroups": TC_ORDINARY_CLUB_GROUPS}
                for cid in tc_ordinary_club_sets()]
    return [club, nation] + grades + clubs + nations + specials + [moments] + ordinary''')
    compile(source,'http_config.py','exec')
    return source


def main():
    original=(SERVER/'http_config.py').read_bytes()
    proposed=transform(original.decode('utf8')).encode('utf8')
    (ROOT/'baseline-http.py').write_bytes(original)
    (ROOT/'http_config.prepared.py').write_bytes(proposed)
    result=dict(status='PREPARED_SERVER_DELTA',baseline_sha256=hashlib.sha256(original).hexdigest(),
        proposed_sha256=hashlib.sha256(proposed).hexdigest(),transformer_sha256=sha(Path(__file__)),
        formal_files_written=False,client_resources_changed=False,state_shop_written=False)
    (ROOT/'prepared.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    print(json.dumps(result))


if __name__=='__main__':main()
