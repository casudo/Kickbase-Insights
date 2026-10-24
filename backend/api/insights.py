"""Builds the API responses from the database.

Everything here only reads. The results only change when a sync finishes, so the API caches them
per league, viewer and sync timestamp (see `api.routes`). The viewer matters for what only they may
see: their real budget and their own bids.
"""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime

from sqlmodel import Session, select

from api.schemas import (
    BattleEntryOut,
    BattleOut,
    ChartManager,
    ChartOut,
    FixturesOut,
    ManagerOut,
    MarketPlayerOut,
    MatchdayChartsOut,
    MatchOut,
    PlayerDetailOut,
    PlayerOut,
    TeamOut,
    TransferOut,
    TurnoverOut,
)
from core import analytics
from core.config import Settings
from db.models import (
    Battle,
    BattleEntry,
    Fixture,
    League,
    Manager,
    MarketBid,
    MarketListing,
    MarketValueHistory,
    MatchdayRanking,
    Player,
    SquadEntry,
    Team,
    Transfer,
    UserLeague,
)


class Insights:
    def __init__(self, settings: Settings, session: Session, league: League, viewer_id: str | None = None):
        self.settings = settings
        self.session = session
        self.league = league
        self.league_id = league.id
        self.viewer_id = viewer_id

    ### ================================================================================================
    ### Shared lookups
    ### ================================================================================================

    def _managers(self) -> list[Manager]:
        return list(self.session.exec(select(Manager).where(Manager.league_id == self.league_id)))

    def _name_to_id(self) -> dict[str, str]:
        return {m.name: m.id for m in self._managers()}

    def _histories(self, player_ids: list[str] | None = None) -> dict[str, list]:
        query = select(MarketValueHistory.player_id, MarketValueHistory.points)
        if player_ids is not None:
            query = query.where(MarketValueHistory.player_id.in_(player_ids))
        return dict(self.session.exec(query).all())

    def season_start(self) -> datetime | None:
        """KBI_KICKBASE__START_DATE if set. Otherwise the first stored transfer or the first kick-off."""
        if self.settings.kickbase.start_date:
            return self.settings.kickbase.start_date.astimezone(UTC)
        first_transfer = self.session.exec(
            select(Transfer.date).where(Transfer.league_id == self.league_id).order_by(Transfer.date).limit(1)
        ).first()
        first_kickoff = self.session.exec(
            select(Fixture.kickoff)
            .where(Fixture.competition_id == self.league.competition_id, Fixture.kickoff.is_not(None))
            .order_by(Fixture.kickoff)
            .limit(1)
        ).first()
        candidates = [d for d in (first_transfer, first_kickoff) if d is not None]
        return min(candidates) if candidates else None

    def _transfer_records(self) -> list[analytics.TransferRecord]:
        rows = self.session.exec(select(Transfer).where(Transfer.league_id == self.league_id))
        records = [
            analytics.TransferRecord(
                t.id, t.date, t.player_id, t.player_name, t.team_id, t.buyer, t.seller, t.price
            )
            for t in rows
        ]
        ### Only an explicit KBI_KICKBASE__START_DATE cuts transfers off, a guessed start drops nothing
        start = self.settings.kickbase.start_date
        return analytics.transfers_since(records, start.astimezone(UTC) if start else None)

    def _player_out(
        self,
        player: Player,
        mv_history: list | None,
        squad: dict[str, SquadEntry],
        market_ids: set[str],
        model: type[PlayerOut] = PlayerOut,
        **extra,
    ) -> PlayerOut:
        owner = squad.get(player.id)
        return model(
            id=player.id,
            first_name=player.first_name,
            last_name=player.last_name,
            team_id=player.team_id,
            image=player.image,
            position=player.position,
            status=player.status,
            status_text=player.status_text,
            market_value=player.market_value,
            trend=player.market_value_trend,
            total_points=player.total_points,
            average_points=player.average_points,
            goals=player.goals,
            assists=player.assists,
            active=player.active,
            owner_id=owner.manager_id if owner else None,
            purchase_price=owner.purchase_price if owner else None,
            on_market=player.id in market_ids,
            **analytics.market_value_deltas(mv_history or []),
            **extra,
        )

    def _squad(self) -> dict[str, SquadEntry]:
        return {
            e.player_id: e
            for e in self.session.exec(select(SquadEntry).where(SquadEntry.league_id == self.league_id))
        }

    def _market(self) -> dict[str, MarketListing]:
        return {
            listing.player_id: listing
            for listing in self.session.exec(
                select(MarketListing).where(MarketListing.league_id == self.league_id)
            )
        }

    ### ================================================================================================
    ### Endpoints
    ### ================================================================================================

    def teams(self) -> list[TeamOut]:
        teams = self.session.exec(
            select(Team).where(Team.competition_id == self.league.competition_id).order_by(Team.placement)
        )
        return [TeamOut.model_validate(team) for team in teams]

    def players(self) -> list[PlayerOut]:
        squad = self._squad()
        market = self._market()
        histories = self._histories()
        result = []
        for player in self.session.exec(select(Player)):
            ### Players who left the competition only matter while someone still owns or sells them
            if not player.active and player.id not in squad and player.id not in market:
                continue
            result.append(self._player_out(player, histories.get(player.id), squad, set(market)))
        result.sort(key=lambda p: p.market_value, reverse=True)
        return result

    def player(self, player_id: str) -> PlayerDetailOut | None:
        player = self.session.get(Player, player_id)
        if player is None:
            return None
        history = self._histories([player_id]).get(player_id) or []
        name_to_id = self._name_to_id()
        transfers = self.session.exec(
            select(Transfer)
            .where(Transfer.league_id == self.league_id, Transfer.player_id == player_id)
            .order_by(Transfer.date.desc())
        )
        return self._player_out(
            player,
            history,
            self._squad(),
            set(self._market()),
            PlayerDetailOut,
            history=[(analytics.day_to_date(day).isoformat(), value) for day, value in history],
            transfers=[self._transfer_out(t, name_to_id) for t in transfers],
        )

    def market(self) -> list[MarketPlayerOut]:
        listings = self._market()
        players = {p.id: p for p in self.session.exec(select(Player).where(Player.id.in_(list(listings))))}
        histories = self._histories(list(listings))
        squad = self._squad()
        own_bids = (
            dict(
                self.session.exec(
                    select(MarketBid.player_id, MarketBid.price).where(
                        MarketBid.league_id == self.league_id, MarketBid.user_id == self.viewer_id
                    )
                ).all()
            )
            if self.viewer_id
            else {}
        )
        result = []
        for listing in listings.values():
            player = players.get(listing.player_id)
            if player is None:
                continue
            result.append(
                self._player_out(
                    player,
                    histories.get(player.id),
                    squad,
                    set(listings),
                    MarketPlayerOut,
                    seller_id=listing.seller_id,
                    seller_name=listing.seller_name,
                    price=listing.price,
                    offer_count=listing.offer_count,
                    own_bid=own_bids.get(listing.player_id),
                    expires_at=listing.expires_at,
                    listed_at=listing.listed_at,
                    is_free_agent=listing.seller_id is None,
                )
            )
        far_future = datetime.max.replace(tzinfo=UTC)
        result.sort(key=lambda p: (p.expires_at or far_future, -p.market_value))
        return result

    def _transfer_out(self, t: Transfer, name_to_id: dict[str, str]) -> TransferOut:
        return TransferOut(
            id=t.id,
            date=t.date,
            player_id=t.player_id,
            player_name=t.player_name,
            team_id=t.team_id,
            buyer=t.buyer,
            buyer_id=name_to_id.get(t.buyer) if t.buyer else None,
            seller=t.seller,
            seller_id=name_to_id.get(t.seller) if t.seller else None,
            price=t.price,
        )

    def transfers(self) -> list[TransferOut]:
        name_to_id = self._name_to_id()
        rows = self.session.exec(
            select(Transfer).where(Transfer.league_id == self.league_id).order_by(Transfer.date.desc())
        )
        start = self.settings.kickbase.start_date
        return [self._transfer_out(t, name_to_id) for t in rows if start is None or t.date >= start]

    def _turnovers(self) -> list[analytics.Turnover]:
        season_start = self.season_start()
        start_day = analytics.day_number(season_start) if season_start else None
        events = analytics.transfer_events(self._transfer_records())
        sold_ids = list({e.player_id for e in events if e.kind == "sell"})
        histories = self._histories(sold_ids)

        def starter_price(player_id: str) -> int | None:
            if start_day is None:
                return None
            return analytics.value_on_day(histories.get(player_id) or [], start_day)

        return analytics.pair_turnovers(events, starter_price, season_start)

    def turnovers(self) -> list[TurnoverOut]:
        name_to_id = self._name_to_id()
        turnovers = self._turnovers()
        players = {
            p.id: p
            for p in self.session.exec(
                select(Player).where(Player.id.in_(list({t.player_id for t in turnovers})))
            )
        }
        result = []
        for t in turnovers:
            player = players.get(t.player_id)
            result.append(
                TurnoverOut(
                    manager=t.manager,
                    manager_id=name_to_id.get(t.manager),
                    player_id=t.player_id,
                    player_name=(player.last_name if player else None) or t.player_name,
                    first_name=player.first_name if player else None,
                    image=player.image if player else None,
                    team_id=t.team_id or (player.team_id if player else None),
                    position=player.position if player else None,
                    buy_price=t.buy_price,
                    buy_date=t.buy_date,
                    bought_from=t.bought_from,
                    starter=t.starter,
                    sell_price=t.sell_price,
                    sell_date=t.sell_date,
                    sold_to=t.sold_to,
                    profit=t.profit,
                    days_held=t.days_held,
                )
            )
        result.sort(key=lambda t: t.sell_date, reverse=True)
        return result

    def managers(self, balances: bool = True) -> list[ManagerOut]:
        """Without `balances` the estimated balances and max bids of the others stay empty, the
        viewer's own figures are always there."""
        managers = self._managers()
        events = analytics.transfer_events(self._transfer_records())
        turnovers = self._turnovers()
        squad_sizes = Counter(e.manager_id for e in self._squad().values())
        start_money = self.settings.kickbase.start_money
        ### The real budget is private, it is only ever shown to its owner
        own_budget = None
        if self.viewer_id:
            membership = self.session.get(UserLeague, (self.viewer_id, self.league_id))
            own_budget = membership.budget if membership else None

        managers.sort(key=lambda m: (m.points is None, -(m.points or 0)))
        leader_points = managers[0].points if managers and managers[0].points is not None else None
        result = []
        previous_points: int | None = None
        for manager in managers:
            own_events = [e for e in events if e.manager == manager.name]
            estimated = analytics.estimate_balance(manager.name, own_events, start_money)
            is_self = manager.id == self.viewer_id
            budget = own_budget if is_self else None
            balance = budget if budget is not None else estimated
            shown = balances or is_self
            profits = [t.profit for t in turnovers if t.manager == manager.name and t.profit is not None]
            result.append(
                ManagerOut(
                    id=manager.id,
                    name=manager.name,
                    image=manager.image,
                    is_self=is_self,
                    placement=manager.placement,
                    points=manager.points,
                    points_behind=(
                        previous_points - manager.points
                        if previous_points is not None and manager.points is not None
                        else 0
                        if leader_points is not None
                        else None
                    ),
                    average_points=manager.average_points,
                    team_value=manager.team_value,
                    matchday_wins=manager.matchday_wins,
                    budget=budget,
                    estimated_balance=estimated if shown else None,
                    max_bid=analytics.max_bid(balance, manager.team_value or 0) if shown else None,
                    squad_size=squad_sizes.get(manager.id, 0),
                    transfers=len(own_events),
                    bought=sum(1 for e in own_events if e.kind == "buy"),
                    sold=sum(1 for e in own_events if e.kind == "sell"),
                    transfer_profit=sum(profits) if profits else 0,
                )
            )
            previous_points = manager.points
        return result

    def battles(self) -> list[BattleOut]:
        managers = {m.id: m for m in self._managers()}
        battles = self.session.exec(
            select(Battle).where(Battle.league_id == self.league_id).order_by(Battle.sort_order)
        ).all()
        entries = self.session.exec(select(BattleEntry).where(BattleEntry.league_id == self.league_id)).all()
        result = []
        for battle in battles:
            rows = [e for e in entries if e.type == battle.type]
            rows.sort(key=lambda e: (e.placement is None, e.placement or 0))
            result.append(
                BattleOut(
                    type=battle.type,
                    name=battle.name,
                    description=battle.description,
                    entries=[
                        BattleEntryOut(
                            manager_id=e.manager_id,
                            name=managers[e.manager_id].name if e.manager_id in managers else e.manager_id,
                            image=managers[e.manager_id].image if e.manager_id in managers else None,
                            placement=e.placement,
                            value=e.value,
                        )
                        for e in rows
                    ],
                )
            )
        return result

    def _chart_managers(self) -> list[ChartManager]:
        return [
            ChartManager(id=m.id, name=m.name)
            for m in sorted(self._managers(), key=lambda m: m.name.casefold())
        ]

    def revenue_chart(self) -> ChartOut:
        managers = self._chart_managers()
        names = {m.name: m.id for m in managers}
        turnovers = self._turnovers()
        start = self.season_start() or (min((t.sell_date for t in turnovers), default=datetime.now(UTC)))
        rows = analytics.cumulative_profit_rows(
            turnovers, list(names), start.astimezone(UTC).date(), datetime.now(UTC).date()
        )
        ### Key the series by manager id: names are free text and could collide with "date"
        return ChartOut(
            managers=managers,
            rows=[
                {"date": row["date"], **{names[n]: v for n, v in row.items() if n != "date"}} for row in rows
            ],
        )

    def matchday_charts(self) -> MatchdayChartsOut:
        managers = self._chart_managers()
        rankings = self.session.exec(
            select(MatchdayRanking)
            .where(MatchdayRanking.league_id == self.league_id)
            .order_by(MatchdayRanking.day)
        ).all()
        by_day: dict[int, list[MatchdayRanking]] = {}
        for ranking in rankings:
            by_day.setdefault(ranking.day, []).append(ranking)

        def rows(attribute: str) -> list[dict]:
            return [
                {"day": day, **{r.manager_id: getattr(r, attribute) for r in entries}}
                for day, entries in sorted(by_day.items())
            ]

        return MatchdayChartsOut(
            managers=managers,
            team_values=rows("team_value"),
            points=rows("points"),
            placements=rows("placement"),
        )

    def fixtures(self, day: int | None) -> FixturesOut:
        current = self.league.current_day
        wanted = day or current
        matches = self.session.exec(
            select(Fixture)
            .where(Fixture.competition_id == self.league.competition_id, Fixture.day == wanted)
            .order_by(Fixture.kickoff, Fixture.id)
        ).all()
        return FixturesOut(
            day=wanted,
            current_day=current,
            number_of_days=self.league.number_of_days,
            matches=[MatchOut.model_validate(m) for m in matches],
        )
