import type { ColumnDef } from "@tanstack/react-table"
import { useMemo, useState } from "react"
import { useManagerMap, useManagers, usePlayers, useTeams } from "@/api/hooks"
import type { Player } from "@/api/types"
import { DataTable, numberColumn } from "@/components/DataTable"
import { Avatar, Delta, Money, PlayerCell, TrendIcon } from "@/components/kickbase"
import { usePlayerSheet } from "@/components/PlayerSheet"
import { Card, Chips, PageHeader, QueryState, SearchInput, Segmented, Select } from "@/components/ui"
import { compactMoney, number } from "@/lib/format"
import { playerName, POSITIONS } from "@/lib/kickbase"

type Filter = "all" | "taken" | "free" | "mine"

const POSITION_CHIPS = Object.entries(POSITIONS).map(([value, meta]) => ({ value: Number(value), label: meta.short }))

export default function Players() {
  const query = usePlayers()
  return (
    <>
      <PageHeader
        title="Spieler"
        description="Marktwerte, Veränderungen und Besitzer aller Spieler der Liga. Tippe auf einen Spieler für Details."
      />
      <QueryState query={query}>{(players) => <PlayersView players={players} />}</QueryState>
    </>
  )
}

function PlayersView({ players }: { players: Player[] }) {
  const managers = useManagerMap()
  const { data: managerList = [] } = useManagers()
  const { data: teams = [] } = useTeams()
  const { open } = usePlayerSheet()
  const own = managerList.find((m) => m.isSelf)

  const [filter, setFilter] = useState<Filter>("all")
  const [positions, setPositions] = useState<number[]>([])
  const [team, setTeam] = useState("")
  const [owner, setOwner] = useState("")
  const [search, setSearch] = useState("")

  const counts = useMemo(
    () => ({
      all: players.length,
      taken: players.filter((p) => p.ownerId).length,
      free: players.filter((p) => !p.ownerId).length,
      mine: own ? players.filter((p) => p.ownerId === own.id).length : 0,
    }),
    [players, own],
  )

  const rows = useMemo(() => {
    const needle = search.trim().toLowerCase()
    return players.filter((p) => {
      if (filter === "taken" && !p.ownerId) return false
      if (filter === "free" && p.ownerId) return false
      if (filter === "mine" && (!own || p.ownerId !== own.id)) return false
      if (positions.length && !positions.includes(p.position)) return false
      if (team && p.teamId !== team) return false
      if (owner && p.ownerId !== owner) return false
      if (needle && !playerName(p).toLowerCase().includes(needle)) return false
      return true
    })
  }, [players, filter, positions, team, owner, search, own])

  const columns = useMemo<ColumnDef<Player, any>[]>(
    () => [
      {
        id: "player",
        header: "Spieler",
        accessorFn: (p) => playerName(p),
        cell: ({ row }) => <PlayerCell player={row.original} />,
      },
      numberColumn<Player>("marketValue", "Marktwert", (p) => p.marketValue, (v, p) => (
        <span className="inline-flex items-center gap-1.5">
          <Money value={v} />
          <TrendIcon value={p.trend} />
        </span>
      )),
      numberColumn<Player>("today", "Heute", (p) => p.today, (v) => <Delta value={v} compact />),
      numberColumn<Player>("yesterday", "Gestern", (p) => p.yesterday, (v) => <Delta value={v} compact />, { hideBelow: "2xl" }),
      numberColumn<Player>("twoDays", "Vorgestern", (p) => p.twoDays, (v) => <Delta value={v} compact />, { hideBelow: "2xl" }),
      numberColumn<Player>("sevenDays", "7 Tage", (p) => p.sevenDays, (v) => <Delta value={v} compact />, { hideBelow: "md" }),
      numberColumn<Player>("thirtyDays", "30 Tage", (p) => p.thirtyDays, (v) => <Delta value={v} compact />, { hideBelow: "lg" }),
      numberColumn<Player>("totalPoints", "Punkte", (p) => p.totalPoints, (v) => <span className="tabular-nums">{number(v)}</span>, {
        hideBelow: "lg",
      }),
      numberColumn<Player>("averagePoints", "Ø", (p) => p.averagePoints, (v) => <span className="tabular-nums">{number(v)}</span>, {
        hideBelow: "xl",
      }),
      {
        id: "owner",
        header: "Besitzer",
        accessorFn: (p) => (p.ownerId ? managers.get(p.ownerId)?.name : undefined),
        sortUndefined: "last",
        cell: ({ row }) => {
          const manager = row.original.ownerId ? managers.get(row.original.ownerId) : undefined
          return manager ? (
            <span className="inline-flex items-center gap-2">
              <Avatar name={manager.name} image={manager.image} size={22} />
              <span className="max-w-32 truncate">{manager.name}</span>
            </span>
          ) : (
            <span className="text-muted">frei</span>
          )
        },
        meta: { hideBelow: "md" },
      },
      numberColumn<Player>(
        "gain",
        "Seit Kauf",
        (p) => (p.purchasePrice != null ? p.marketValue - p.purchasePrice : null),
        (v, p) => (
          <span title={p.purchasePrice != null ? `Kaufpreis ${compactMoney(p.purchasePrice)}` : undefined}>
            <Delta value={v} compact />
          </span>
        ),
        { hideBelow: "2xl" },
      ),
    ],
    [managers],
  )

  return (
    <Card>
      <div className="space-y-3 p-4 sm:p-5">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <Segmented
            value={filter}
            onChange={setFilter}
            options={[
              { value: "all", label: "Alle", count: counts.all },
              { value: "taken", label: "Vergeben", count: counts.taken },
              { value: "free", label: "Frei", count: counts.free },
              ...(own ? [{ value: "mine" as const, label: "Mein Kader", count: counts.mine }] : []),
            ]}
          />
          <SearchInput value={search} onChange={setSearch} placeholder="Spieler suchen …" className="lg:w-64" />
        </div>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
          <Chips options={POSITION_CHIPS} selected={positions} onChange={setPositions} />
          <div className="grid flex-1 grid-cols-2 gap-2 sm:ml-auto sm:max-w-md">
            <Select
              label="Verein"
              value={team}
              onChange={setTeam}
              options={[
                { value: "", label: "Alle Vereine" },
                ...[...teams].sort((a, b) => a.name.localeCompare(b.name)).map((t) => ({ value: t.id, label: t.name })),
              ]}
            />
            <Select
              label="Besitzer"
              value={owner}
              onChange={setOwner}
              options={[{ value: "", label: "Alle Manager" }, ...managerList.map((m) => ({ value: m.id, label: m.name }))]}
            />
          </div>
        </div>
      </div>
      <DataTable
        data={rows}
        columns={columns}
        initialSorting={[{ id: "today", desc: true }]}
        getRowId={(p) => p.id}
        onRowClick={(p) => open(p.id)}
        mobileCard={(p) => <PlayerCard player={p} ownerName={p.ownerId ? managers.get(p.ownerId)?.name : undefined} />}
      />
    </Card>
  )
}

function PlayerCard({ player, ownerName }: { player: Player; ownerName?: string }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <PlayerCell player={player} sub={<span className="truncate">{ownerName ?? "frei"}</span>} />
      <div className="shrink-0 text-right">
        <div className="flex items-center justify-end gap-1 text-sm font-semibold tabular-nums">
          {compactMoney(player.marketValue)}
          <TrendIcon value={player.trend} className="size-3.5" />
        </div>
        <div className="text-xs">
          <Delta value={player.today} compact />
        </div>
      </div>
    </div>
  )
}
