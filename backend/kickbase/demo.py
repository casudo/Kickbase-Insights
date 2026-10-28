"""A fake Kickbase API with generated sample data.

Used by the tests and by `KBI_DEMO=true`, which runs the whole app without a Kickbase account.

One competition with all players is shared by two leagues, each with its own managers, squads,
transfers, market and rankings. The only login is `demo@demo.de` with the password `demo`, as "Du", who
is in both leagues. Budgets and bids are private: the API only reveals them to their owner, exactly
like Kickbase does.
"""

from __future__ import annotations

import json
import random
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

import httpx

from core.analytics import day_number

TEAMS = [
    ("2", "Bayern", "FCB"),
    ("3", "Dortmund", "BVB"),
    ("4", "Frankfurt", "SGE"),
    ("5", "Freiburg", "SCF"),
    ("7", "Leverkusen", "B04"),
    ("9", "Stuttgart", "VFB"),
    ("10", "Bremen", "SVW"),
    ("11", "Wolfsburg", "WOB"),
    ("13", "Augsburg", "FCA"),
    ("14", "Hoffenheim", "TSG"),
    ("15", "Gladbach", "BMG"),
    ("18", "Mainz", "M05"),
    ("28", "Köln", "KOE"),
    ("39", "St. Pauli", "STP"),
    ("40", "Union Berlin", "FCU"),
    ("43", "Leipzig", "RBL"),
    ("50", "Heidenheim", "FCH"),
    ("51", "Hamburg", "HSV"),
]
### Kickbase's own placeholder pictures (a mannequin in the club's kit) for players without a photo.
### Demo players are made up, so they never get a real person's face.
KIT_IMAGES = {
    "2": "48622993193e45f09d696908d75ed523",
    "3": "ed209b2ca67c4784a658521f80baa795",
    "4": "3b8eae1b9d6d4e8d961bfd3f152db402",
    "5": "7d6a4935195d414a9119e81aa398222a",
    "7": "353820bceb58462590ea1a470cde9cc6",
    "9": "2dea6714f704489fa0fb302accce4e8a",
    "10": "1a88a39549924d048294f618079e8437",
    "11": "a00a1472afdc4462933a364537704b05",
    "13": "b93977fb3dee4e75af09d67896a1666b",
    "14": "1fe930ae579e4ba78fe7c4f948264d3b",
    "15": "d4b8e5025d3043b3ad48c1f6ac91830d",
    "18": "0563ba9a260a4fd0a9c193dc525529b3",
    "40": "98159e30baca4a1080128a7a4c32914e",
    "43": "fe5ccc7927254a46ab71aeed829805e4",
    "50": "ef0f480acb2e4002811381446d78ae87",
}

FIRST_NAMES = """
    Lukas Jonas Leon Finn Elias Noah Paul Ben Luis Felix Maximilian Jan Tim Niklas Moritz David
    Julian Tom Erik Malte Marco Kevin Florian Mats Robin Sandro Dario Mateo Rafael Hugo Kenan Emre
    Yann Aurel Omar Jesper
""".split()  # noqa: SIM905 - a word list reads better than 100 quoted strings
LAST_NAMES = """
    Becker Hoffmann Schulz Wagner Krüger Neumann Schwarz Zimmermann Braun Hartmann Lange Werner
    Krause Meier Lehmann Köhler Herrmann Walter Peters Möller Kaiser Fuchs Lang Scholz Jung Hahn
    Vogel Friedrich Keller Günther Frank Berger Winkler Roth Beck Lorenz Baumann Franke Albrecht
    Schuster Simon Ludwig Böhm Winter Kraus Martin Schumacher Krämer Vogt Stein Jäger Otto Sommer
    Groß Seidel Heinrich Brandt Haas Schreiber Graf Dietrich Ziegler Kuhn Pohl Engel
""".split()  # noqa: SIM905 - a word list reads better than 100 quoted strings

USERS = {
    "1001": "Du",
    "1002": "Tiki Taka Toni",
    "1003": "Catenaccio Carla",
    "1004": "Gegenpress Gerd",
    "1005": "Abseitsfalle Anna",
    "1006": "Fallrückzieher Felix",
    "1007": "Konter Kalle",
    "1008": "Libero Lea",
    "2001": "Flanken Franz",
    "2002": "Doppelpass Doris",
    "2003": "Elfmeter Emil",
    "2004": "Zehner Zoe",
}
LEAGUE_ID = "4242"
SECOND_LEAGUE_ID = "4343"
LEAGUES = {
    LEAGUE_ID: ("Demo Liga", ["1001", "1002", "1003", "1004", "1005", "1006", "1007", "1008"]),
    SECOND_LEAGUE_ID: ("Stammtisch", ["1001", "1003", "2001", "2002", "2003", "2004"]),
}
### The managers of the first league, as (id, name)
MANAGERS = [(uid, USERS[uid]) for uid in LEAGUES[LEAGUE_ID][1]]
OWN_ID = "1001"

BATTLES = [
    (4, "Saubermann", "Die meisten Punkte mit dem Torwart"),
    (5, "Abwehrbollwerk", "Die meisten Punkte mit Abwehrspielern"),
    (6, "Fädenzieher", "Die meisten Punkte mit Mittelfeldspielern"),
    (7, "Angriffslustig", "Die meisten Punkte mit Angreifern"),
    (8, "Punktejäger", "Die meisten Punkte an einem Spieltag"),
]
EVENT_TYPES = [
    (1, "Goal (Striker)"),
    (2, "Assist (Midfielder)"),
    (3, "Yellow Card"),
    (4, "Red Card"),
    (5, "Shot on goal"),
    (6, "Pass final Third"),
    (7, "Interception"),
    (8, "Possession lost"),
    (9, "Clean Sheet"),
    (10, "Game Won"),
    (11, "Played Minutes Bonus"),
    (12, "Goal conceded"),
]
### Squad composition per position: goalkeeper, defender, midfielder, forward
SQUAD_QUOTA = {1: 2, 2: 5, 3: 5, 4: 3}
TEAM_QUOTA = {1: 3, 2: 7, 3: 7, 4: 5}
LINEUP_QUOTA = {1: 1, 2: 4, 3: 4, 4: 2}
CURRENT_DAY = 8
NUMBER_OF_DAYS = 34
### Kick-off of the nine matches of a matchday, relative to the start of that matchday
MATCH_OFFSETS = [timedelta(hours=h) for h in (0, 21, 21, 21, 21, 24, 45, 47, 48)]


### The one login of the demo
DEMO_EMAIL = "demo@demo.de"
DEMO_PASSWORD = "demo"


@dataclass
class DemoPlayer:
    id: str
    first_name: str
    last_name: str
    team_id: str
    position: int
    status: int
    market_value: int
    trend: int
    history: list[list[int]]
    average_points: int
    total_points: int
    goals: int
    assists: int
    ### A photo of the player's own. Like Kickbase, only the player details carry it.
    photo: str | None = None

    @property
    def image(self) -> str | None:
        kit = KIT_IMAGES.get(self.team_id)
        return f"content/file/{kit}.png" if kit else None


class DemoLeague:
    """Managers, squads, transfers, market and rankings of one league."""

    def __init__(self, world: DemoWorld, league_id: str, seed: int):
        self.world = world
        self.id = league_id
        self.name, member_ids = LEAGUES[league_id]
        self.managers = [(uid, USERS[uid]) for uid in member_ids]
        rng = random.Random(seed)
        players = world.players

        by_position: dict[int, list[DemoPlayer]] = {p: [] for p in SQUAD_QUOTA}
        for player in players.values():
            by_position[player.position].append(player)
        for pool in by_position.values():
            rng.shuffle(pool)

        ### Squads: most players were assigned at the season start, the rest bought from Kickbase
        ### manager id -> (player id, purchase price, bought at or None for players assigned at the start)
        self.squads: dict[str, list[tuple[str, int, datetime | None]]] = {}
        self.transfers: list[dict] = []
        start_day = day_number(world.season_start)
        for manager_id, manager_name in self.managers:
            squad: list[tuple[str, int, datetime | None]] = []
            for position, count in SQUAD_QUOTA.items():
                for _ in range(count):
                    player = by_position[position].pop()
                    if rng.random() < 0.6:
                        squad.append((player.id, world.value_on(player, start_day), None))
                    else:
                        when = world.season_start + timedelta(
                            days=rng.uniform(2, 50), minutes=rng.randint(0, 600)
                        )
                        price = int(world.value_on(player, day_number(when)) * rng.uniform(1.0, 1.15))
                        squad.append((player.id, price, when))
                        self._transfer(when, player, price, buyer=manager_name)
            self.squads[manager_id] = squad

            ### Players this manager already sold again: starters and players bought earlier
            for _ in range(rng.randint(2, 5)):
                player = by_position[rng.choice([2, 3, 4])].pop()
                sold = world.season_start + timedelta(days=rng.uniform(5, 54), minutes=rng.randint(0, 600))
                if rng.random() < 0.5:
                    bought = world.season_start + timedelta(
                        days=rng.uniform(1, (sold - world.season_start).days)
                    )
                    buy_price = int(world.value_on(player, day_number(bought)) * rng.uniform(1.0, 1.1))
                    self._transfer(bought, player, buy_price, buyer=manager_name)
                sell_price = int(world.value_on(player, day_number(sold)) * rng.uniform(0.95, 1.0))
                self._transfer(sold, player, sell_price, seller=manager_name)

        ### A few trades between managers: the buyer keeps the player. Only starters are traded, so
        ### the trade can never predate the seller's own purchase.
        names = dict(self.managers)
        for _ in range(4):
            seller_id, buyer_id = rng.sample([m for m, _ in self.managers], 2)
            starters = [index for index, entry in enumerate(self.squads[seller_id]) if entry[2] is None]
            if not starters:
                continue
            player_id, _, _ = self.squads[seller_id].pop(rng.choice(starters))
            player = players[player_id]
            when = world.now - timedelta(days=rng.uniform(1, 12))
            price = int(world.value_on(player, day_number(when)) * rng.uniform(1.0, 1.2))
            self._transfer(when, player, price, buyer=names[buyer_id], seller=names[seller_id])
            self.squads[buyer_id].append((player_id, price, when))

        self.transfers.sort(key=lambda item: item["dt"], reverse=True)
        owned = {entry[0] for squad in self.squads.values() for entry in squad}

        ### Market: free players from Kickbase plus a few listed by managers. Some carry bids, each
        ### visible to its bidder only.
        free = [p for p in players.values() if p.id not in owned and p.market_value > 1_000_000]
        rng.shuffle(free)
        member_ids = [uid for uid, _ in self.managers]
        bidders = {1: OWN_ID, 4: OWN_ID, 2: member_ids[1], 6: member_ids[2]}
        self.market: list[dict] = []
        for index, player in enumerate(free[:14]):
            entry = _market_entry(player, player.market_value)
            entry["exs"] = rng.randint(1800, 3 * 86400)
            entry["dt"] = _iso(world.now - timedelta(hours=rng.randint(1, 40)))
            if index in bidders:
                entry["_bid"] = (bidders[index], int(player.market_value * rng.uniform(1.02, 1.12)))
            self.market.append(entry)
        for manager_id, manager_name in self.managers[2:6]:
            player_id = self.squads[manager_id][rng.randrange(len(self.squads[manager_id]))][0]
            player = players[player_id]
            entry = _market_entry(player, int(player.market_value * rng.uniform(1.0, 1.3)))
            entry["u"] = {"i": manager_id, "n": manager_name}
            entry["dt"] = _iso(world.now - timedelta(hours=rng.randint(1, 30)))
            self.market.append(entry)

        self.budgets = {uid: rng.randint(-2_000_000, 12_000_000) for uid in member_ids}
        if self.id == LEAGUE_ID:
            self.budgets[OWN_ID] = 3_412_500

        ### Rankings per matchday
        self.lineups = {
            mid: self._lineup(rng, [entry[0] for entry in squad]) for mid, squad in self.squads.items()
        }
        self.rankings: dict[int, list[dict]] = {}
        totals = dict.fromkeys(member_ids, 0)
        for day in range(1, CURRENT_DAY + 1):
            day_points = {}
            for manager_id in member_ids:
                if day < CURRENT_DAY:
                    day_points[manager_id] = rng.randint(250, 1350)
                else:
                    day_points[manager_id] = sum(
                        world.live_points(pid)[0] for pid in self.lineups[manager_id] if pid
                    )
                totals[manager_id] += day_points[manager_id]
            season_order = sorted(totals, key=totals.get, reverse=True)
            day_order = sorted(day_points, key=day_points.get, reverse=True)
            rows = []
            for manager_id, manager_name in self.managers:
                squad_value = sum(players[entry[0]].market_value for entry in self.squads[manager_id])
                drift = 1 - (CURRENT_DAY - day) * rng.uniform(0.004, 0.02)
                rows.append(
                    {
                        "i": manager_id,
                        "n": manager_name,
                        "uim": None,
                        "sp": totals[manager_id],
                        "mdp": day_points[manager_id],
                        "tv": int(squad_value * drift),
                        "spl": season_order.index(manager_id) + 1,
                        "mdpl": day_order.index(manager_id) + 1,
                        "lp": self.lineups[manager_id],
                    }
                )
            self.rankings[day] = rows

        self.battle_values = {
            battle_type: {mid: rng.randint(400, 3200) for mid in member_ids} for battle_type, _, _ in BATTLES
        }

    def _transfer(self, when: datetime, player: DemoPlayer, price: int, *, buyer=None, seller=None) -> None:
        data = {"pi": player.id, "pn": player.last_name, "tid": player.team_id, "trp": price}
        if buyer:
            data["byr"] = buyer
        if seller:
            data["slr"] = seller
        ### Feed ids are unique across leagues, like Kickbase's
        item_id = f"{self.id}{len(self.transfers):06d}"
        self.transfers.append({"i": item_id, "t": 15, "dt": _iso(when), "data": data})

    def _lineup(self, rng: random.Random, squad: list[str]) -> list[str | None]:
        lineup: list[str | None] = []
        for position, count in LINEUP_QUOTA.items():
            options = [pid for pid in squad if self.world.players[pid].position == position]
            rng.shuffle(options)
            picked = options[:count]
            lineup.extend(picked + [None] * (count - len(picked)))
        return lineup

    def market_for(self, user_id: str) -> list[dict]:
        """The market as `user_id` sees it: with their own offers and nobody else's."""
        result = []
        for entry in self.market:
            item = {k: v for k, v in entry.items() if k != "_bid"}
            bid = entry.get("_bid")
            if bid and bid[0] == user_id:
                item["ofs"] = [{"i": self.offer_id(entry["i"]), "u": user_id, "uop": bid[1]}]
            result.append(item)
        return result

    def offer_id(self, player_id: str) -> str:
        return f"{self.id}{player_id}"

    def offer(
        self, method: str, user_id: str, player_id: str, offer_id: str | None, body: dict
    ) -> httpx.Response:
        """Places, changes or withdraws `user_id`'s offer, with Kickbase's rule that an offer for a
        player sold by Kickbase is at least worth the market value."""
        entry = next((item for item in self.market if item["i"] == player_id), None)
        if entry is None:
            return httpx.Response(404, json={"err": 1, "errMsg": "Der Spieler steht nicht auf dem Markt."})
        if method == "DELETE":
            bid = entry.get("_bid")
            if not bid or bid[0] != user_id or offer_id != self.offer_id(player_id):
                return httpx.Response(404, json={"err": 2, "errMsg": "Dieses Gebot gibt es nicht."})
            del entry["_bid"]
            return httpx.Response(200, json={})
        price = int(body.get("price") or 0)
        minimum = entry["mv"] if "u" not in entry else 1
        if price < minimum:
            return httpx.Response(400, json={"err": 3, "errMsg": "Das Gebot liegt unter dem Marktwert."})
        entry["_bid"] = (user_id, price)
        return httpx.Response(200, json={"offerId": self.offer_id(player_id)})


@dataclass
class DemoWorld:
    now: datetime = field(default_factory=lambda: datetime.now(UTC).replace(microsecond=0))
    seed: int = 7

    def __post_init__(self) -> None:
        rng = random.Random(self.seed)
        today = day_number(self.now)
        ### Matchday CURRENT_DAY started 22 hours ago, so some games are over, some running, some ahead
        self.current_start = self.now - timedelta(hours=22)
        self.season_start = self.current_start - timedelta(days=7 * (CURRENT_DAY - 1) + 4)
        self._fixtures = self._build_fixtures()

        self.players: dict[str, DemoPlayer] = {}
        next_id = 100
        for team_id, _, _ in TEAMS:
            for position, count in TEAM_QUOTA.items():
                for _ in range(count):
                    next_id += rng.randint(1, 9)
                    base = rng.lognormvariate(15.4 if position > 1 else 14.6, 0.9)
                    value = int(min(max(base, 500_000), 70_000_000))
                    history = self._history(rng, value, today)
                    status = rng.choices([0, 1, 2, 4, 256], weights=[86, 5, 5, 2, 2])[0]
                    average = rng.randint(20, 160) if value > 2_000_000 else rng.randint(0, 60)
                    trend = (
                        1 if history[-1][1] > history[-2][1] else 2 if history[-1][1] < history[-2][1] else 0
                    )
                    self.players[str(next_id)] = DemoPlayer(
                        id=str(next_id),
                        first_name=rng.choice(FIRST_NAMES),
                        last_name=rng.choice(LAST_NAMES),
                        team_id=team_id,
                        position=position,
                        status=status,
                        market_value=history[-1][1],
                        trend=trend,
                        history=history,
                        average_points=average,
                        total_points=average * (CURRENT_DAY - 1),
                        goals=rng.randint(0, 6) if position >= 3 else rng.randint(0, 1),
                        assists=rng.randint(0, 5) if position >= 2 else 0,
                    )

        self.leagues = {
            league_id: DemoLeague(self, league_id, self.seed * 31 + index)
            for index, league_id in enumerate(LEAGUES)
        }

    ### The first league, for the tests that only need one
    @property
    def league(self) -> DemoLeague:
        return self.leagues[LEAGUE_ID]

    @property
    def squads(self):
        return self.league.squads

    @property
    def transfers(self):
        return self.league.transfers

    @property
    def market(self):
        return self.league.market

    ### ---------------------------------------------------------------------------
    ### Helpers

    @staticmethod
    def _history(rng: random.Random, value: int, today: int) -> list[list[int]]:
        values = [value]
        for _ in range(364):
            values.append(max(500_000, int(values[-1] * (1 + rng.gauss(0, 0.025)))))
        values.reverse()
        return [[today - 364 + index, v] for index, v in enumerate(values)]

    @staticmethod
    def value_on(player: DemoPlayer, day: int) -> int:
        for point_day, value in reversed(player.history):
            if point_day <= day:
                return value
        return player.history[0][1]

    def fixtures(self) -> list[dict]:
        return self._fixtures

    def _build_fixtures(self) -> list[dict]:
        days = []
        team_ids = [team_id for team_id, _, _ in TEAMS]
        symbols = {team_id: symbol for team_id, _, symbol in TEAMS}
        for day in range(1, NUMBER_OF_DAYS + 1):
            rng = random.Random(self.seed * 1000 + day)
            order = team_ids[:]
            rng.shuffle(order)
            start = self.current_start + timedelta(days=7 * (day - CURRENT_DAY))
            matches = []
            for index in range(9):
                kickoff = start + MATCH_OFFSETS[index]
                team1, team2 = order[index * 2], order[index * 2 + 1]
                status = 2 if kickoff + timedelta(hours=2) <= self.now else 1 if kickoff <= self.now else 0
                goals = (rng.randint(0, 4), rng.randint(0, 3)) if status else (None, None)
                matches.append(
                    {
                        "mi": f"{day:02d}{index}",
                        "day": day,
                        "dt": _iso(kickoff),
                        "t1": team1,
                        "t2": team2,
                        "t1sy": symbols[team1],
                        "t2sy": symbols[team2],
                        "t1g": goals[0],
                        "t2g": goals[1],
                        "st": status,
                        "mtd": "90" if status == 2 else str(rng.randint(10, 85)) if status else None,
                    }
                )
            days.append({"day": day, "it": matches})
        return days

    def match_of(self, team_id: str, day: int = CURRENT_DAY) -> dict | None:
        for match in self.fixtures()[day - 1]["it"]:
            if team_id in (match["t1"], match["t2"]):
                return match
        return None

    def match_role(self, player_id: str) -> int:
        """The player's part in the current match, coded like Kickbase: 5 in the starting eleven,
        3 came on, 4 did not play, 0 before the kick-off."""
        match = self.match_of(self.players[player_id].team_id)
        if not match or match["st"] == 0:
            return 0
        return random.Random(f"{self.seed}-role-{player_id}").choices([5, 3, 4], weights=[70, 12, 18])[0]

    def live_points(self, player_id: str) -> tuple[int, list[dict], dict | None]:
        player = self.players[player_id]
        match = self.match_of(player.team_id)
        if not match or self.match_role(player_id) in (0, 4):
            return 0, [], match
        rng = random.Random(f"{self.seed}-{player_id}")
        events = []
        for _ in range(rng.randint(3, 9)):
            event_type = rng.choice([5, 6, 7, 8, 11])
            points = {5: 12, 6: 1, 7: 4, 8: -1, 11: 20}[event_type]
            events.append(
                {
                    "ei": str(rng.randint(10**6, 10**7)),
                    "eti": event_type,
                    "p": points,
                    "mt": rng.randint(1, 90),
                }
            )
        if player.position >= 3 and rng.random() < 0.25:
            events.append({"ei": str(rng.randint(10**6, 10**7)), "eti": 1, "p": 80, "mt": rng.randint(1, 90)})
        if rng.random() < 0.15:
            events.append({"ei": str(rng.randint(10**6, 10**7)), "eti": 2, "p": 60, "mt": rng.randint(1, 90)})
        if rng.random() < 0.12:
            events.append(
                {"ei": str(rng.randint(10**6, 10**7)), "eti": 3, "p": -20, "mt": rng.randint(1, 90)}
            )
        events.sort(key=lambda e: e["mt"], reverse=True)
        return sum(e["p"] for e in events), events, match

    ### ---------------------------------------------------------------------------
    ### Routing

    def handle(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/v4/user/login":
            return self._login(request)

        auth = request.headers.get("authorization", "")
        user_id = auth.removeprefix("Bearer demo-") if auth.startswith("Bearer demo-") else None
        if user_id not in USERS:
            return httpx.Response(401, json={"err": "unauthorized"})

        offer = re.fullmatch(r"/v4/leagues/(\w+)/market/(\w+)/offers(?:/(\w+))?", path)
        if offer and request.method in ("POST", "DELETE"):
            league = self.leagues.get(offer.group(1))
            if league is None or user_id not in dict(league.managers):
                return httpx.Response(403, json={"err": "not a member"})
            body = json.loads(request.content or b"{}") if request.method == "POST" else {}
            return league.offer(request.method, user_id, offer.group(2), offer.group(3), body)

        for pattern, handler in self._routes():
            match = re.fullmatch(pattern, path)
            if match:
                groups = match.groups()
                if pattern.startswith(r"/v4/leagues/(\w+)"):
                    league = self.leagues.get(groups[0])
                    if league is None or user_id not in dict(league.managers):
                        return httpx.Response(403, json={"err": "not a member"})
                    return httpx.Response(200, json=handler(request.url.params, user_id, league, *groups[1:]))
                return httpx.Response(200, json=handler(request.url.params, user_id, *groups))
        return httpx.Response(404, json={"err": "not found"})

    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self.handle)

    def _login(self, request: httpx.Request) -> httpx.Response:
        try:
            body = json.loads(request.content or b"{}")
        except ValueError:
            body = {}
        email = str(body.get("em", "")).strip().casefold()
        if email != DEMO_EMAIL or body.get("pass") != DEMO_PASSWORD:
            return httpx.Response(401, json={"err": "wrong credentials"})
        return httpx.Response(
            200,
            json={
                "u": {"id": OWN_ID, "name": USERS[OWN_ID], "email": DEMO_EMAIL},
                "tkn": f"demo-{OWN_ID}",
                "tknex": _iso(self.now + timedelta(days=7)),
            },
        )

    def _routes(self):
        return [
            (r"/v4/leagues/selection", self._selection),
            (r"/v4/leagues/(\w+)/overview", self._overview),
            (r"/v4/leagues/(\w+)/me/budget", lambda q, uid, league: {"b": league.budgets[uid]}),
            (r"/v4/leagues/(\w+)/managers/(\w+)/dashboard", self._dashboard),
            (r"/v4/leagues/(\w+)/managers/(\w+)/squad", self._squad),
            (r"/v4/leagues/(\w+)/battles/(\d+)/users", self._battle),
            (r"/v4/leagues/(\w+)/ranking", self._ranking),
            (r"/v4/leagues/(\w+)/market", self._market),
            (r"/v4/leagues/(\w+)/activitiesFeed/?", self._feed),
            (r"/v4/bonus/collect", lambda q, uid: {"it": []}),
            (r"/v4/competitions/(\d+)/table", self._table),
            (
                r"/v4/competitions/(\d+)/matchdays",
                lambda q, uid, cid: {"day": CURRENT_DAY, "it": self.fixtures()},
            ),
            (r"/v4/competitions/(\d+)/teams/(\w+)/teamprofile", self._team_profile),
            (r"/v4/competitions/(\d+)/players/(\w+)/marketValue/(\d+)", self._history_response),
            (r"/v4/competitions/(\d+)/players/(\w+)/performance", self._performance),
            (r"/v4/competitions/(\d+)/players/(\w+)", self._player),
            (r"/v4/competitions/(\d+)/playercenter/(\w+)", self._player_center),
            (
                r"/v4/live/eventtypes",
                lambda q, uid: {"it": [{"i": i, "ti": name} for i, name in EVENT_TYPES]},
            ),
        ]

    def _selection(self, query, user_id):
        return {
            "it": [
                {"i": league.id, "n": league.name, "cpi": "1", "gpm": 1}
                for league in self.leagues.values()
                if user_id in dict(league.managers)
            ]
        }

    def _overview(self, query, user_id, league: DemoLeague):
        return {
            "i": league.id,
            "lnm": league.name,
            "cpi": "1",
            "b": 50_000_000,
            "us": [{"i": mid, "n": name, "uim": None} for mid, name in league.managers],
            "btls": [{"t": t, "n": n, "d": d} for t, n, d in BATTLES],
        }

    def _market(self, query, user_id, league: DemoLeague):
        return {
            "it": league.market_for(user_id),
            "mvud": _iso(self.now.replace(hour=20, minute=0, second=0) - timedelta(days=1)),
            "day": CURRENT_DAY,
        }

    def _dashboard(self, query, user_id, league: DemoLeague, manager_id):
        latest = next(row for row in league.rankings[CURRENT_DAY] if row["i"] == manager_id)
        wins = sum(
            1
            for day in range(1, CURRENT_DAY)
            for row in league.rankings[day]
            if row["i"] == manager_id and row["mdpl"] == 1
        )
        return {
            "u": manager_id,
            "unm": USERS[manager_id],
            "ap": latest["sp"] // CURRENT_DAY,
            "tp": latest["sp"],
            "mdw": wins,
            "pl": latest["spl"],
            "tv": latest["tv"],
        }

    def _squad(self, query, user_id, league: DemoLeague, manager_id):
        items = []
        for player_id, price, _ in league.squads.get(manager_id, []):
            p = self.players[player_id]
            items.append(
                {
                    "pi": p.id,
                    "pn": p.last_name,
                    "tid": p.team_id,
                    "pos": p.position,
                    "st": p.status,
                    "p": p.total_points,
                    "ap": p.average_points,
                    "mv": p.market_value,
                    "mvt": p.trend,
                    "prc": price,
                    "mvgl": p.market_value - price,
                    "pim": p.image,
                }
            )
        return {"u": manager_id, "unm": USERS[manager_id], "it": items}

    def _battle(self, query, user_id, league: DemoLeague, battle_type):
        values = league.battle_values.get(int(battle_type), {})
        order = sorted(values, key=values.get, reverse=True)
        return {
            "us": [
                {"u": {"i": mid, "n": USERS[mid]}, "pl": index + 1, "v": values[mid]}
                for index, mid in enumerate(order)
            ]
        }

    def _ranking(self, query, user_id, league: DemoLeague):
        day = int(query.get("dayNumber") or CURRENT_DAY)
        return {"us": league.rankings.get(day, []), "day": day, "nd": NUMBER_OF_DAYS, "sn": "26/27"}

    def _feed(self, query, user_id, league: DemoLeague):
        start = int(query.get("start", 0))
        size = min(int(query.get("max", 26)), 26)
        return {"af": league.transfers[start : start + size]}

    def _table(self, query, user_id, competition_id):
        rng = random.Random(self.seed)
        rows = [
            {
                "tid": tid,
                "tn": name,
                "cp": rng.randint(2, 20),
                "mc": CURRENT_DAY - 1,
                "gd": rng.randint(-12, 15),
            }
            for tid, name, _ in TEAMS
        ]
        rows.sort(key=lambda row: (row["cp"], row["gd"]), reverse=True)
        for index, row in enumerate(rows):
            row["cpl"] = index + 1
        return {"it": rows}

    def _team_profile(self, query, user_id, competition_id, team_id):
        name = next(n for tid, n, _ in TEAMS if tid == team_id)
        return {
            "tid": team_id,
            "tn": name,
            "it": [
                {
                    "i": p.id,
                    "n": p.last_name,
                    "tid": p.team_id,
                    "pos": p.position,
                    "st": p.status,
                    "mv": p.market_value,
                    "mvt": p.trend,
                    "ap": p.average_points,
                    "sdmvt": p.history[-1][1] - p.history[-2][1],
                    "pim": p.image,
                }
                for p in self.players.values()
                if p.team_id == team_id
            ],
        }

    def _player(self, query, user_id, competition_id, player_id):
        p = self.players[player_id]
        notes = {
            1: "Muskelfaserriss - fällt wochenlang aus",
            2: "Angeschlagen",
            4: "Aufbautraining",
            256: "Abwesend",
        }
        return {
            "i": p.id,
            "fn": p.first_name,
            "ln": p.last_name,
            "tid": p.team_id,
            "pos": p.position,
            "st": p.status,
            "stxt": notes.get(p.status),
            "tp": p.total_points,
            "ap": p.average_points,
            "g": p.goals,
            "a": p.assists,
            "mv": p.market_value,
            "mvt": p.trend,
            "pim": p.photo or p.image,
        }

    def _history_response(self, query, user_id, competition_id, player_id, days):
        history = self.players[player_id].history[-int(days) :]
        return {"it": [{"dt": day, "mv": value} for day, value in history]}

    def _performance(self, query, user_id, competition_id, player_id):
        """The player's season, shaped like Kickbase's: every match of the club, played or not."""
        player = self.players[player_id]
        matches = []
        for group in self.fixtures():
            match = next((m for m in group["it"] if player.team_id in (m["t1"], m["t2"])), None)
            if match is None:
                continue
            entry = {
                "day": group["day"],
                "md": match["dt"],
                "t1": match["t1"],
                "t2": match["t2"],
                "mdst": match["st"],
                "cur": group["day"] == CURRENT_DAY,
                "st": 0,
            }
            if match["st"]:
                ### Like Kickbase, the player's club only comes with the matches already played
                entry.update({"t1g": match["t1g"], "t2g": match["t2g"], "pt": player.team_id})
                if group["day"] == CURRENT_DAY:
                    role, points = self.match_role(player_id), self.live_points(player_id)[0]
                else:
                    rng = random.Random(f"{self.seed}-day-{group['day']}-{player_id}")
                    role = rng.choices([5, 3, 4], weights=[70, 12, 18])[0]
                    average = player.average_points or 60
                    points = max(-40, int(rng.gauss(average, average * 0.7))) if role != 4 else 0
                played = {
                    5: rng_minutes(player_id, group["day"], 75, 96),
                    3: rng_minutes(player_id, group["day"], 5, 40),
                }.get(role, 0)
                entry.update({"st": role, "mp": f"{played}'"})
                if points:
                    entry["p"] = points
            matches.append(entry)
        return {"it": [{"ti": "2026/2027", "n": "Bundesliga", "ph": matches}]}

    def _player_center(self, query, user_id, competition_id, player_id):
        p = self.players[player_id]
        points, events, match = self.live_points(player_id)
        role = self.match_role(player_id)
        clock = int(match["mtd"]) if match and match["mtd"] else 0
        ### Minutes played: the whole match so far, from the substitution on, or none
        came_on = random.Random(f"{self.seed}-sub-{player_id}").randint(5, 40)
        played = {5: clock, 3: max(1, clock - came_on), 4: 0}
        return {
            "i": p.id,
            "tid": p.team_id,
            "n": p.last_name,
            "p": points,
            "events": events,
            "t1": match["t1"] if match else None,
            "t2": match["t2"] if match else None,
            "t1g": match["t1g"] if match else None,
            "t2g": match["t2g"] if match else None,
            "st": role,
            "mt": played.get(role),
            "mtd": match["mtd"] if match else None,
            "mst": match["st"] if match else None,
            "md": match["dt"] if match else None,
            "pim": p.image,
        }


def rng_minutes(player_id: str, day: int, low: int, high: int) -> int:
    return random.Random(f"minutes-{day}-{player_id}").randint(low, high)


def _market_entry(player: DemoPlayer, price: int) -> dict:
    return {
        "i": player.id,
        "fn": player.first_name,
        "n": player.last_name,
        "tid": player.team_id,
        "pos": player.position,
        "st": player.status,
        "mv": player.market_value,
        "mvt": player.trend,
        "p": player.total_points,
        "ap": player.average_points,
        "ofc": 0,
        "prc": price,
        "pim": player.image,
    }


def _iso(value: datetime) -> str:
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
