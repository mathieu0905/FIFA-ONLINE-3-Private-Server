"""Liga sponsor theme challenge; install after league_reward_guard.

All reward mutations run inside the guard's staged-state, single-commit hooks.
No hook reads state from disk, invokes a handler, or calls _save.  Existing
seasons and original sponsor EP missions are intentionally left unchanged.
"""
from collections import Counter
from contextlib import closing
import functools
import json

VERSION = 1
SPONSOR_ID = "3"
MISSION_ID = "101"
CHALLENGE_ID = "club8_win3"
REQUIRED_CLUB_PLAYERS = 8
TARGET_WINS = 3
REWARD_CASH = 120
REWARD_TABLE_KEY = "theme_cash_only"
STATE_KEY = "theme_challenge"
SNAPSHOT_KEY = "theme_challenge_snapshot"
TITLE_KEY = "THEME_CLUB8_WIN3_TITLE"
PROGRESS_KEY = "THEME_CLUB8_WIN3_PROGRESS"


def _int(value):
    if isinstance(value, bool):
        return None
    try:
        result = int(value)
        return result if float(value) == result else None
    except (TypeError, ValueError, OverflowError):
        return None


def install(hc):
    if getattr(hc, "_offline_theme_challenges_installed", False):
        return
    if not callable(getattr(hc, "register_reward_hook", None)):
        raise RuntimeError("Install league_reward_guard with safe reward hooks first")
    if not callable(getattr(hc, "add_cash", None)):
        raise RuntimeError("Install the cash economy before theme challenges")

    def owner(st):
        return str(hc.my_coach(st)["_id"])

    def active(st):
        lg = st.get("league2") or {}
        challenge = lg.get(STATE_KEY)
        if not isinstance(challenge, dict):
            return None
        if (challenge.get("version") != VERSION
                or challenge.get("id") != CHALLENGE_ID
                or challenge.get("season_id") != lg.get("season_instance_id")
                or challenge.get("owner") != owner(st)
                or str(lg.get("season_owner_id")) != owner(st)
                or str(lg.get("sponsor")) != SPONSOR_ID):
            return None
        return challenge

    def calendar_before_commit(st, req, out):
        # The guard has already assigned a fresh, server-generated season id.
        if not out.get("result") or str(req.get("sponsor")) != SPONSOR_ID:
            return
        lg = st["league2"]
        if str(lg.get("sponsor")) != SPONSOR_ID:
            return
        if not lg.get("season_instance_id") or str(lg.get("season_owner_id")) != owner(st):
            raise RuntimeError("Theme challenge needs the guarded season identity")
        lg[STATE_KEY] = {
            "version": VERSION, "id": CHALLENGE_ID,
            "season_id": lg["season_instance_id"], "owner": owner(st),
            "wins": 0, "target": TARGET_WINS,
            "reward_cash": REWARD_CASH, "reward_paid": False,
            "processed_matches": {}, "last_theme_count": 0,
        }
        out["resources"] = hc.l2_resources(st)

    def pending_fixture(st, match):
        lg = st.get("league2") or {}
        pending = lg.get("pending") or {}
        league = lg.get("league") or {}
        param = match.get("leagueparam") or {}
        mid = str(match.get("id") or "")
        if not mid or pending.get("id") != mid:
            return None
        rnd = _int(pending.get("round"))
        maximum = _int(league.get("maxround"))
        home, away = _int(pending.get("home")), _int(pending.get("away"))
        if rnd is None or maximum is None or not 0 <= rnd <= maximum or home is None or away is None:
            return None
        if (param.get("matchtype") != "league"
                or _int(param.get("round")) != rnd
                or _int(param.get("home")) != home or _int(param.get("away")) != away):
            return None
        expected = {(h, a) for h, a in hc.league_round(league.get("teams") or [], rnd)
                    if h is not None and a is not None}
        if (home, away) not in expected or hc.my_teamid(st) not in (home, away):
            return None
        # A newly manufactured match id cannot replay an already completed round.
        if any(_int(r.get("round")) == rnd and r.get("home") == home and r.get("away") == away
               for r in league.get("matchrecords") or []):
            return None
        return {"round": rnd, "home": home, "away": away}

    def snapshot(st, match, challenge):
        result = {
            "version": VERSION, "id": CHALLENGE_ID,
            "mid": str(match.get("id") or ""),
            "season_id": challenge["season_id"], "owner": challenge["owner"],
            "match_type": match.get("type"),
            "eligible": False, "club_count": 0, "members": [],
        }
        if (match.get("type") != "League_2_league"
                or match.get("simulated")
                or (match.get("gamesettings") or {}).get("simulated")):
            result["reason"] = "not_manual_league"
            return result
        fixture = pending_fixture(st, match)
        if fixture is None:
            result["reason"] = "no_valid_pending_fixture"
            return result
        result["fixture"] = fixture
        sides = [(key, side) for key, side in (match.get("side") or {}).items()
                 if any(str(p.get("id")) == owner(st) for p in side.get("players") or [])]
        if len(sides) != 1:
            result["reason"] = "ambiguous_owner_side"
            return result
        side_key, side = sides[0]
        my_team = _int((side.get("team") or {}).get("teamid"))
        if my_team != hc.my_teamid(st):
            result["reason"] = "wrong_owner_club"
            return result
        result.update(side=side_key, my_teamid=my_team)
        # ep_match_squad rebuilds both copies; the rendered team.squad is authoritative.
        squad = (side.get("team") or {}).get("squad") or {}
        if side.get("squad") != squad:
            result["reason"] = "inconsistent_match_squad"
            return result
        positions = squad.get("positions") or []
        starters = [p for p in positions if _int(p.get("pos")) is not None
                    and 0 <= _int(p.get("pos")) < hc.POS_SUB]
        if len(starters) != 11 or len({_int(p.get("pos")) for p in starters}) != 11:
            result["reason"] = "incomplete_starting_eleven"
            return result
        owned = {str(hc.iid(p)): p for p in st["teams"][str(hc._default_slot(st))]["players"]}
        match_cards = {str(p.get("id") or p.get("_id") or p.get("spid")): p
                       for p in (side.get("team") or {}).get("players") or []}
        members = []
        for position in starters:
            card_id = str(position.get("id") or position.get("spid"))
            card, match_card = owned.get(card_id), match_cards.get(card_id)
            if card is None or match_card is None:
                result["reason"] = "unowned_starting_card"
                return result
            spid = _int(card.get("spid"))
            if (spid is None or _int(match_card.get("spid")) != spid
                    or ("spid" in position and _int(position["spid"]) != spid)):
                result["reason"] = "starting_spid_mismatch"
                return result
            members.append({"card_id": card_id, "spid": spid, "pos": _int(position["pos"])})
        if len({m["card_id"] for m in members}) != 11:
            result["reason"] = "duplicate_starting_card"
            return result
        spids = [m["spid"] for m in members]
        with closing(hc._db()) as connection:
            rows = connection.execute(
                "SELECT spid, playerid, teamid FROM players WHERE spid IN (%s)" %
                ",".join("?" for _ in spids), spids).fetchall()
        database = {int(row[0]): (int(row[1]), _int(row[2])) for row in rows}
        if len(database) != 11:
            result["reason"] = "unknown_database_player"
            return result
        for member in members:
            member["playerid"], member["club"] = database[member["spid"]]
        if len({m["playerid"] for m in members}) != 11:
            result["reason"] = "duplicate_real_player"
            return result
        clubs = Counter(m["club"] for m in members if m["club"] is not None and m["club"] > 0)
        club, count = clubs.most_common(1)[0] if clubs else (None, 0)
        result.update(members=members, club=club, club_count=count,
                      eligible=count >= REQUIRED_CLUB_PLAYERS, reason="ok")
        return result

    def match_playing(st, match, req):
        challenge = active(st)
        if challenge is None or SNAPSHOT_KEY in match:
            return
        frozen = snapshot(st, match, challenge)
        match[SNAPSHOT_KEY] = frozen
        challenge["last_theme_count"] = frozen["club_count"]

    def completed_fixture(st, match, frozen, req):
        fixture = frozen.get("fixture") or {}
        home, away = fixture.get("home"), fixture.get("away")
        values = {}
        for key in ("home", "away"):
            row = req.get(key) or {}
            tid, score = _int(row.get("id")), _int(row.get("score"))
            if tid is None or score is None or not 0 <= score <= 999 or tid in values:
                return None
            values[tid] = score
        if set(values) != {home, away}:
            return None
        my_team = frozen.get("my_teamid")
        if my_team not in values:
            return None
        records = ((st.get("league2") or {}).get("league") or {}).get("matchrecords") or []
        expected_goals = {"home": values[home], "away": values[away]}
        if not any(r.get("round") == fixture.get("round") and r.get("home") == home
                   and r.get("away") == away and r.get("goals") == expected_goals for r in records):
            return None
        return values[my_team] > values[away if my_team == home else home]

    def match_before_commit(st, match, req, out):
        challenge = active(st)
        frozen = match.get(SNAPSHOT_KEY) or {}
        mid = str(match.get("id") or "")
        if (challenge is None or not out.get("result") or not frozen.get("eligible")
                or frozen.get("version") != VERSION or frozen.get("id") != CHALLENGE_ID
                or frozen.get("mid") != mid or frozen.get("season_id") != challenge["season_id"]
                or frozen.get("owner") != challenge["owner"]
                or frozen.get("match_type") != "League_2_league" or match.get("type") != "League_2_league"
                or match.get("stage") != "closed" or match.get("simulated")
                or (match.get("gamesettings") or {}).get("simulated")):
            return
        processed = challenge["processed_matches"]
        if mid in processed:
            return
        won = completed_fixture(st, match, frozen, req)
        if won is None:
            return
        processed[mid] = {"won": won, "round": frozen["fixture"]["round"]}
        if won:
            challenge["wins"] = min(TARGET_WINS, challenge["wins"] + 1)
        reward = 0
        if challenge["wins"] >= TARGET_WINS and not challenge["reward_paid"]:
            # This flag, the cash mutation and the guard receipt share the sole _save.
            challenge["reward_paid"] = True
            challenge["reward_mid"] = mid
            hc.add_cash(st, REWARD_CASH, "theme:" + CHALLENGE_ID + ":" + challenge["season_id"])
            reward = REWARD_CASH
        out["theme_challenge"] = {
            "id": CHALLENGE_ID, "missionid": MISSION_ID,
            "wins": challenge["wins"], "target": TARGET_WINS,
            "achievement": challenge["reward_paid"], "cashreward": reward,
        }

    removers = [hc.register_reward_hook("calendar_before_commit", calendar_before_commit),
                hc.register_reward_hook("match_playing", match_playing),
                hc.register_reward_hook("match_before_commit", match_before_commit)]

    original_sponsor = hc.ep_l2_sponsor
    original_achievement = hc.ep_l2_achievement
    original_file = hc.from_file
    original_me = hc.l2_me

    @functools.wraps(original_me)
    def league_me(st):
        out = original_me(st)
        challenge = active(st)
        if challenge is not None:
            out[STATE_KEY] = {"id": CHALLENGE_ID, "missionid": MISSION_ID,
                              "wins": challenge["wins"], "target": TARGET_WINS,
                              "achievement": challenge["reward_paid"], "reward_cash": REWARD_CASH}
        return out

    def decoded(response):
        content_type, data = response
        return content_type, json.loads(data)

    @functools.wraps(original_sponsor)
    def sponsor(difficulty, query, body):
        _, out = decoded(original_sponsor(difficulty, query, body))
        for offer in out.get("sponsors") or []:
            if str(offer.get("sponsorid")) == SPONSOR_ID:
                missions = offer.setdefault("missions", [])
                if not any(str(m.get("mid")) == MISSION_ID for m in missions):
                    missions.append({"mid": MISSION_ID})
        return hc._json(out)

    @functools.wraps(original_achievement)
    def achievement(query, body):
        with hc.STATE_LOCK:
            st = hc._state()
            _, out = decoded(original_achievement(query, body))
            challenge = active(st)
            if challenge is not None:
                out.setdefault("missions", []).append({
                    "mid": MISSION_ID, "achievement": bool(challenge["reward_paid"]),
                    "progress": [challenge["wins"], TARGET_WINS,
                                 challenge["last_theme_count"], REQUIRED_CLUB_PLAYERS],
                })
            return hc._json(out)

    @functools.wraps(original_file)
    def static_file(path):
        result = original_file(path)
        if path not in ("/static/db/LEAGUE2SPONSOR", "/static/db/LEAGUE2REWARD") or result is None:
            return result
        content_type, out = decoded(result)
        if content_type != "application/json":
            return result
        if path == "/static/db/LEAGUE2SPONSOR":
            out.setdefault("mission", {})[MISSION_ID] = {
                "title": TITLE_KEY, "lv1": str(TARGET_WINS),
                "reward_lv1": REWARD_TABLE_KEY, "progress": PROGRESS_KEY,
            }
        else:
            # Creation UI sums every mission's reward count as EP.  The challenge
            # pays cash separately, so give it a complete, explicitly zero-EP row.
            sponsors = out.setdefault("sponsor", {})
            difficulties = {str(d) for d in range(10, 25)}
            templates = {}
            for key, rewards in sponsors.items():
                if key == REWARD_TABLE_KEY or not isinstance(rewards, dict):
                    continue
                for difficulty, reward in rewards.items():
                    if isinstance(reward, dict):
                        difficulties.add(str(difficulty))
                        templates.setdefault(str(difficulty), reward)
            sponsors[REWARD_TABLE_KEY] = {
                difficulty: dict(templates.get(difficulty, {}), count=0)
                for difficulty in sorted(difficulties)
            }
        return hc._json(out)

    hc.ep_l2_sponsor = sponsor
    hc.l2_me = league_me
    hc.ep_l2_achievement = achievement
    hc.from_file = static_file
    hc.ENDPOINTS["/league2/sponsor/achievement"] = achievement
    hc.ROUTES = [(pattern, sponsor if fn is original_sponsor else fn) for pattern, fn in hc.ROUTES]
    hc.theme_challenge_active = active
    hc.theme_challenge_hooks = {
        "calendar_before_commit": calendar_before_commit,
        "match_playing": match_playing,
        "match_before_commit": match_before_commit,
    }
    hc.theme_challenge_remove_hooks = lambda: [remove() for remove in removers]
    hc._offline_theme_challenges_installed = True
