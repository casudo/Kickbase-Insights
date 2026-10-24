/**
 * Dialog for placing, changing or withdrawing an offer for a player on the market.
 * The offer goes to Kickbase in the name of whoever is logged in, exactly like in the app.
 */

import { AlertTriangle, Gavel } from "lucide-react"
import { type FormEvent, type ReactNode, useState } from "react"
import { useBid, useManagers, useTeamMap } from "@/api/hooks"
import type { MarketPlayer } from "@/api/types"
import { cn } from "@/lib/cn"
import { compactMoney, money } from "@/lib/format"
import { playerName, position } from "@/lib/kickbase"
import { Dialog } from "./Dialog"
import { PlayerAvatar, PositionBadge } from "./kickbase"
import { Button } from "./ui"

/** Market value plus these shares, as one tap amounts */
const STEPS = [0, 0.02, 0.05, 0.1]

const roundUp = (value: number) => Math.ceil(value / 1000) * 1000

export function BidDialog({ player, onClose }: { player: MarketPlayer | null; onClose: () => void }) {
  return (
    <Dialog open={player !== null} onClose={onClose} title={player ? `Gebot für ${playerName(player)}` : "Gebot"} size="small">
      {player && <BidForm key={player.id} player={player} onDone={onClose} />}
    </Dialog>
  )
}

function BidForm({ player, onDone }: { player: MarketPlayer; onDone: () => void }) {
  const managers = useManagers()
  const teams = useTeamMap()
  const { place, withdraw } = useBid()
  const me = managers.data?.find((manager) => manager.isSelf)
  // Kickbase sells at the market value, managers at the price they asked for
  const base = player.isFreeAgent ? player.marketValue : (player.price ?? player.marketValue)
  const [input, setInput] = useState(String(player.ownBid ?? roundUp(base)))
  const amount = Number(input.replace(/\D/g, "")) || 0
  const busy = place.isPending || withdraw.isPending
  const error = place.error ?? withdraw.error
  const belowValue = player.isFreeAgent && amount > 0 && amount < player.marketValue
  const overMax = me?.maxBid != null && amount > me.maxBid

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    if (amount <= 0) return
    try {
      await place.mutateAsync({ playerId: player.id, price: amount })
      onDone()
    } catch {
      // Shown below
    }
  }

  const retract = async () => {
    try {
      await withdraw.mutateAsync(player.id)
      onDone()
    } catch {
      // Shown below
    }
  }

  return (
    <form onSubmit={submit} className="space-y-4 p-5 sm:p-6">
      <div className="flex items-center gap-3 pr-10">
        <PlayerAvatar image={player.image} teamId={player.teamId} size={48} />
        <div className="min-w-0">
          <div className="truncate font-semibold">{playerName(player)}</div>
          <div className="mt-0.5 flex items-center gap-2 text-xs text-muted">
            <PositionBadge value={player.position} />
            <span>{position(player.position).long}</span>
            <span>·</span>
            <span className="truncate">{teams.get(player.teamId ?? "")?.name}</span>
          </div>
        </div>
      </div>

      <dl className="grid grid-cols-2 gap-x-4 gap-y-3 rounded-xl bg-surface-2 p-3 text-sm">
        <Fact label="Marktwert">{money(player.marketValue)}</Fact>
        <Fact label={player.isFreeAgent ? "Verkäufer" : `Preis von ${player.sellerName ?? "?"}`}>
          {player.isFreeAgent ? "Kickbase" : money(player.price)}
        </Fact>
        <Fact label="Dein Kontostand">{me ? compactMoney(me.budget ?? me.estimatedBalance) : "–"}</Fact>
        <Fact label="Dein Max. Gebot">{me ? compactMoney(me.maxBid) : "–"}</Fact>
      </dl>

      <label className="block">
        <span className="mb-1.5 block text-sm font-medium">{player.ownBid != null ? "Dein neues Gebot" : "Dein Gebot"}</span>
        <div className="relative">
          <input
            inputMode="numeric"
            autoFocus
            value={amount ? amount.toLocaleString("de-DE") : ""}
            onChange={(event) => setInput(event.target.value)}
            className="h-11 w-full rounded-xl border border-line bg-surface pr-8 pl-3 text-base font-semibold tabular-nums focus:border-accent focus:outline-none"
          />
          <span className="absolute top-1/2 right-3 -translate-y-1/2 text-sm text-muted">€</span>
        </div>
      </label>
      <div className="grid grid-cols-4 gap-1.5">
        {STEPS.map((step) => {
          const value = roundUp(base * (1 + step))
          return (
            <button
              key={step}
              type="button"
              onClick={() => setInput(String(value))}
              className={cn(
                "h-8 rounded-lg border text-xs font-medium tabular-nums transition-colors",
                amount === value ? "border-accent bg-accent-soft" : "border-line bg-surface hover:bg-surface-2",
              )}
            >
              {step === 0 ? (player.isFreeAgent ? "Marktwert" : "Preis") : `+${step * 100} %`}
            </button>
          )
        })}
      </div>

      {belowValue && <Notice>Kickbase nimmt für seine Spieler nur Gebote ab dem Marktwert an.</Notice>}
      {overMax && <Notice>Das ist mehr als dein Max. Gebot. Kickbase lehnt Gebote ab, die du dir nicht leisten kannst.</Notice>}
      {error && <p className="rounded-xl bg-down/10 px-3 py-2 text-sm text-down">{error.message}</p>}

      <p className="text-xs text-muted">Das Gebot wird in deinem Namen bei Kickbase abgegeben, genau wie in der App.</p>

      <div className="flex flex-wrap items-center justify-end gap-2">
        {player.ownBid != null && (
          <Button variant="ghost" className="mr-auto text-down" onClick={retract} loading={withdraw.isPending} disabled={busy}>
            Gebot zurückziehen
          </Button>
        )}
        <Button onClick={onDone} disabled={busy}>
          Abbrechen
        </Button>
        <Button type="submit" variant="primary" loading={place.isPending} disabled={busy || amount <= 0}>
          {!place.isPending && <Gavel className="size-4" />}
          {player.ownBid != null ? "Gebot ändern" : "Gebot abgeben"}
        </Button>
      </div>
    </form>
  )
}

function Fact({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="min-w-0">
      <dt className="truncate text-xs text-muted">{label}</dt>
      <dd className="font-semibold tabular-nums">{children}</dd>
    </div>
  )
}

function Notice({ children }: { children: ReactNode }) {
  return (
    <p className="flex items-start gap-2 rounded-xl bg-warn/10 px-3 py-2 text-sm text-warn">
      <AlertTriangle className="mt-0.5 size-4 shrink-0" />
      {children}
    </p>
  )
}
