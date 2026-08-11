# START_DATE as a league reset timestamp

Date: 2026-08-11

## Problem

`START_DATE` is a `dd.mm.yyyy` date. A Kickbase league can be reset partway through
a day: squads are re-drawn and everyone starts over. Events from before that reset
are still in the activity feed, so they are counted as transfers and pollute the
revenue numbers. A date cannot express "from 18:00 on 1 August onwards", so there is
no way to draw the line in the right place.

### Evidence from the affected league

The reset happened between `2026-08-01T17:47:43Z` and `2026-08-01T18:10:57Z`.

Three players were sold twice at an identical price, with no purchase in between:

| Player ID | First sale | Second sale | Price |
| --- | --- | --- | --- |
| 3754 | 2026-08-01T16:43:17Z | 2026-08-01T18:20:27Z | 3,565,890 |
| 8289 | 2026-08-01T17:47:43Z | 2026-08-01T18:46:35Z | 500,000 |
| 1767 | 2026-08-01T17:47:34Z | 2026-08-11T10:26:39Z | 500,000 |

A player can only be sold twice if owned twice, and the identical prices rule out a
coincidental repurchase. The 23-minute gap is followed by six sales in 23 seconds
and 30 more within the hour, which is a freshly drawn squad being liquidated.

The exact reset instant is not recoverable: `leagues.transfers()` filters the feed to
`t == 15` and discards the join and matchday event types, so the marker never reaches
disk. `2026-08-01T18:00:00Z` sits inside the gap and is therefore robust to being off
by a few minutes either way.

Four events precede the cutoff. Those are the ones currently distorting the numbers.

## Decisions

1. **ISO 8601 only.** `START_DATE=2026-08-01T18:00:00Z`. A `dd.mm.yyyy` value is a
   hard error. Accepting it as midnight would silently shift results by an arbitrary
   number of hours, which is worse than failing.
2. **Filter at the source.** Pre-cutoff events are dropped before they are written to
   `all_transfers.json`, so nothing downstream ever sees them.

## Design

### One parser

`miscellaneous.get_start_datetime()` reads and parses `START_DATE`, returning a
timezone-aware UTC `datetime` and raising `KickbaseException` with a migration hint on
anything malformed. The value is currently read via `getenv` and parsed three
different ways in three places; after this there is one definition of what it means.

### Filtering

In `turnovers()`, after the cached and freshly fetched transfers are merged and
sorted, drop every item whose `dt` is earlier than the cutoff, then write the cleaned
list back to `all_transfers.json`. Filtering the *merged* list means an existing cache
containing pre-reset events is repaired on the next run without manual deletion. The
number of dropped events is logged at INFO.

### Timezones

Feed timestamps are UTC (`...Z`); the deployment timezone is `Europe/Berlin` (UTC+2 in
August). Both sides are normalized to aware UTC before any comparison, so a naive
versus aware mix cannot shift the boundary by two hours.

### Market value lookups

Two sites match a player's market value against the start date, and market values
exist only per day. They use the *date part* of the timestamp; the event cutoff uses
the full instant. One setting, two granularities, deliberately.

### Call sites

- `main.py` startup validation
- `main.py` `taken_free_players()` — assigned-player buy price
- `main.py` `turnovers()` — starter market value, simulated buy date, new filter
- `miscellaneous.py` `calculate_revenue_data_daily()` — the revenue graph anchors its
  start point at START_DATE. Found during implementation, not in the original list;
  it would have crashed on the run after `turnovers()` succeeded. Its end anchor used
  a naive `datetime.now()` against a UTC-labelled series, so it was also shifted by the
  local timezone offset; both anchors are now aware UTC.
- `entrypoint.py` — env validation, via the shared parser
- `README.md` — variable table, migration callout and all four Docker examples
- `.env.example`

## Testing

Stubbed, no live API calls:

- pre-cutoff events dropped from a merged cache
- post-cutoff events kept
- an event exactly at the cutoff is kept (boundary is inclusive)
- valid ISO parses to the expected aware UTC instant
- `dd.mm.yyyy` rejected with the migration hint
- missing value rejected
- the cleaned cache is actually written back

## Migration

Existing deployments must change `START_DATE` to ISO 8601. The error message names the
offending value and shows the expected form. `all_transfers.json` repairs itself on the
next run.

## Out of scope

- Recovering the exact reset instant from unfiltered feed event types
- Applying the cutoff to `balances()`, `team_value_per_match_day()` or
  `league_user_stats_tables()`; those derive from current API state, not event history
- The dormant live points path
