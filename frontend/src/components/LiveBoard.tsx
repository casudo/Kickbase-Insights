/**
 * The animated live board: the live points as a fullscreen view for a TV or a second screen.
 *
 * Every update of the live data is compared with the one before. A goal, an assist, a card or a big
 * jump in points takes over the scoreboard with a flash, then the points fly into the player's tile,
 * the scores count up and the players and managers slide into their new order. Smaller changes show
 * up as badges on the players. The demo plays made-up moments on top of the real lineups, to see the
 * board at work while no match runs. New data can be held back for a while, so the board does not
 * run ahead of the TV.
 */

import "./live-board.css"
import { FlaskConical, Loader2, Maximize, Minimize, Settings2, X } from "lucide-react"
import { type CSSProperties, type RefObject, useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react"
import { useLive, useTeamMap } from "@/api/hooks"
import type { Live, LiveEventKind, LiveManager, LivePlayer, Match } from "@/api/types"
import { TeamLogo } from "@/components/kickbase"
import { cn } from "@/lib/cn"
import { number, signedNumber, time, weekdayTime } from "@/lib/format"
import { useNow, useStoredState } from "@/lib/hooks"
import { cdnUrl, initials, playerName, pointsGrade, position } from "@/lib/kickbase"
import { useLeague } from "@/lib/league"
import {
  BIG_POINTS,
  boardMatches,
  demoStep,
  diffLive,
  matchClock,
  type Moment,
  type MomentKind,
  planSteps,
  startDemo,
  type Step,
} from "@/lib/liveBoard"

// Timings of one moment. The CSS animations in live-board.css are made to fit these.
const FLASH_MS = 5600
/** Before the points fly, the list glides to the manager when their row is out of sight */
const REVEAL_MS = 700
const FLIGHT_MS = 950
const PLAYER_COUNT_MS = 900
const MANAGER_COUNT_MS = 1800
const BADGE_MS = 2400
const CHIP_MOVE_MS = 1000
const ROW_MOVE_MS = 1400
/** Slow in and out, so rows and players glide instead of jumping off */
const MOVE_EASE = "cubic-bezier(0.65, 0, 0.35, 1)"
const VISIBLE_ROWS = 6
/** Poll a bit faster than the live page while a match runs, the server still asks Kickbase at most every 45 seconds */
const RUNNING_REFRESH_MS = 30_000

/** What the viewer set up for the board, kept in the browser */
type BoardSettings = {
  /** Holds new data back, so the board does not show a goal before the TV does */
  delay: boolean
  delaySeconds: number
  /** The kinds of moments that take over the scoreboard, the others show as a badge on the player */
  flash: Record<MomentKind, boolean>
}
const DEFAULT_SETTINGS: BoardSettings = {
  delay: true,
  delaySeconds: 30,
  flash: { goal: true, ownGoal: true, assist: true, yellow: true, yellowRed: true, red: true, points: true },
}

/** The choices for the big animation, in the settings' order. `mark` is the sign shown next to it. */
const FLASH_OPTIONS: { kind: MomentKind; label: string; mark: LiveEventKind | null }[] = [
  { kind: "goal", label: "Tore", mark: "goal" },
  { kind: "ownGoal", label: "Eigentore", mark: "own_goal" },
  { kind: "assist", label: "Vorlagen", mark: "assist" },
  { kind: "yellow", label: "Gelbe Karten", mark: "yellow" },
  { kind: "yellowRed", label: "Gelb-Rot", mark: "yellow_red" },
  { kind: "red", label: "Rote Karten", mark: "red" },
  { kind: "points", label: `Sonst ab ±${BIG_POINTS} Punkten`, mark: null },
]
const MAX_DELAY_SECONDS = 600 // 10 minutes
const DELAY_STEP_SECONDS = 5

/** The stored settings on top of the defaults, so settings added later get their default */
function readSettings(stored: Partial<BoardSettings>): BoardSettings {
  const settings = { ...DEFAULT_SETTINGS, ...stored, flash: { ...DEFAULT_SETTINGS.flash, ...stored.flash } }
  const seconds = Math.round(Number(settings.delaySeconds))
  return { ...settings, delaySeconds: Number.isFinite(seconds) ? Math.min(MAX_DELAY_SECONDS, Math.max(0, seconds)) : DEFAULT_SETTINGS.delaySeconds }
}

export default function LiveBoard({ onClose }: { onClose: () => void }) {
  const query = useLive(true, RUNNING_REFRESH_MS)
  const { league } = useLeague()
  const root = useRef<HTMLDivElement>(null)
  const toolbar = useRef<HTMLDivElement>(null)
  const [demo, setDemo] = useState(false)
  const [picked, setPicked] = useState<string | null>(null)
  const [idle, setIdle] = useState(true)
  const [stored, setStored] = useStoredState<Partial<BoardSettings>>("kbi-board-settings", {})
  const settings = readSettings(stored)
  const [settingsOpen, setSettingsOpen] = useState(false)
  /** The player whose events are open, and how they are listed */
  const [playerId, setPlayerId] = useState<string | null>(null)
  const [eventOrder, setEventOrder] = useState<EventOrder>("time")

  const delayMs = settings.delay ? settings.delaySeconds * 1000 : 0
  const delayed = useDelayed(query.data, delayMs)
  // The demo plays on the delayed data too: it keeps the real scores of running matches
  const demoLive = useDemo(demo, delayed ?? undefined, idle)
  const live = (demo ? demoLive : null) ?? delayed
  const key = demo ? "demo" : "live"
  // The board's clocks run as far behind as its data, the demo makes up its own
  const lag = demo ? 0 : delayMs
  const flashKinds = new Set(FLASH_OPTIONS.filter((option) => settings.flash[option.kind]).map((option) => option.kind))
  const engine = useBoardEngine(live, key, root, flashKinds)
  useEffect(() => setIdle(engine.idle), [engine.idle])

  const fullscreen = useFullscreen()
  const restless = useRestless(root)
  useWakeLock()
  useEffect(() => {
    const overflow = document.body.style.overflow
    document.body.style.overflow = "hidden"
    return () => {
      document.body.style.overflow = overflow
    }
  }, [])
  useEffect(() => {
    // Leaving the field first, so a number typed into it counts before the settings go away
    const closeSettings = () => {
      const focused = document.activeElement
      if (focused instanceof HTMLElement && toolbar.current?.contains(focused)) focused.blur()
      setSettingsOpen(false)
    }
    const onKey = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return
      if (settingsOpen) closeSettings()
      else if (playerId) setPlayerId(null)
      else if (!document.fullscreenElement) onClose()
    }
    // The settings close when tapping anywhere outside the controls
    const onPointer = (event: PointerEvent) => {
      if (settingsOpen && !toolbar.current?.contains(event.target as Node)) closeSettings()
    }
    document.addEventListener("keydown", onKey)
    document.addEventListener("pointerdown", onPointer)
    return () => {
      document.removeEventListener("keydown", onKey)
      document.removeEventListener("pointerdown", onPointer)
    }
  }, [onClose, settingsOpen, playerId])

  const close = () => {
    if (document.fullscreenElement) document.exitFullscreen().catch(() => {})
    onClose()
  }

  return (
    <div
      ref={root}
      className={cn("lb-root dark", !restless && !settingsOpen && !playerId && "lb-calm")}
      role="dialog"
      aria-modal="true"
      aria-label="Live-Board"
    >
      <div ref={toolbar} className="lb-toolbar">
        {live && (
          <span className="lb-toolbar-stand">
            Stand {time(live.updatedAt)}
            {lag > 0 && ` · ${settings.delaySeconds} s verzögert`}
          </span>
        )}
        <button
          type="button"
          onClick={() => setDemo(!demo)}
          aria-pressed={demo}
          title={demo ? "Demo beenden" : "Demo starten: ausgedachte Punkte auf den echten Aufstellungen"}
          className={cn("lb-toolbar-button lb-toolbar-wide", demo && "lb-toolbar-active")}
        >
          <FlaskConical className="size-4" />
          {demo ? "Demo beenden" : "Demo"}
        </button>
        <button
          type="button"
          onClick={() => setSettingsOpen(!settingsOpen)}
          aria-expanded={settingsOpen}
          aria-label="Einstellungen"
          title="Einstellungen"
          className={cn("lb-toolbar-button", settingsOpen && "lb-toolbar-active")}
        >
          <Settings2 className="size-4" />
        </button>
        {fullscreen.supported && (
          <button type="button" onClick={fullscreen.toggle} className="lb-toolbar-button" aria-label={fullscreen.active ? "Vollbild beenden" : "Vollbild"}>
            {fullscreen.active ? <Minimize className="size-4" /> : <Maximize className="size-4" />}
          </button>
        )}
        <button type="button" onClick={close} className="lb-toolbar-button" aria-label="Schließen">
          <X className="size-4" />
        </button>
        {settingsOpen && <SettingsPanel settings={settings} onChange={setStored} />}
      </div>

      {engine.view.live ? (
        <Board
          live={engine.view.live}
          sourceKey={key}
          demo={demo}
          leagueName={league?.name ?? ""}
          engine={engine}
          picked={picked}
          onPick={setPicked}
          onOpenPlayer={setPlayerId}
          lag={lag}
        />
      ) : query.error ? (
        <div className="lb-message">
          <p>{query.error instanceof Error ? query.error.message : "Die Live-Daten konnten nicht geladen werden."}</p>
          <button type="button" className="lb-toolbar-button lb-toolbar-wide" onClick={() => query.refetch()}>
            Erneut versuchen
          </button>
        </div>
      ) : (
        <div className="lb-message">
          <Loader2 className="size-6 animate-spin" />
        </div>
      )}

      {/* From the data the board shows, so the events wait for the delay like everything else */}
      {playerId && engine.view.live && (
        <PlayerEvents live={engine.view.live} playerId={playerId} order={eventOrder} onOrder={setEventOrder} onClose={() => setPlayerId(null)} />
      )}

      {/* Sideways and downwards move with different easings, so the points fly in an arc */}
      {engine.flights.map((flight) => (
        <span
          key={flight.id}
          className={cn("lb-flight", flight.points < 0 && "lb-flight-negative")}
          style={{ "--x": `${flight.x}px`, "--y": `${flight.y}px`, "--dx": `${flight.dx}px`, "--dy": `${flight.dy}px` } as CSSProperties}
        >
          <span className="lb-flight-y">
            <span className="lb-flight-text">{signedNumber(flight.points)}</span>
          </span>
        </span>
      ))}
    </div>
  )
}

// ---------------------------------------------------------------------------
// The delay and the settings

type Held = { live: Live; arrived: number }
type Delayed = { shown: Live | null; held: Held[] }

/**
 * Due `delayMs` after Kickbase was asked. At the latest `delayMs` after it got here, in case this
 * device's clock runs behind the server's.
 */
const dueAt = (item: Held, delayMs: number) => Math.min(Date.parse(item.live.updatedAt), item.arrived) + delayMs

/** The newest held back data whose time has come, the older ones are passed over */
function releaseDue(state: Delayed, delayMs: number): Delayed {
  const now = Date.now()
  const ready = state.held.findLastIndex((item) => dueAt(item, delayMs) <= now)
  return ready < 0 ? state : { shown: state.held[ready].live, held: state.held.slice(ready + 1) }
}

/**
 * Holds new live data back until `delayMs` after Kickbase was asked for it, so a goal does not show up
 * on the board before it does on the TV. Everything waits together: points, scores and match clocks.
 * The first data shows right away, so the board opens at once. So does data older than the delay,
 * like the last answer while no match runs.
 */
function useDelayed(live: Live | undefined, delayMs: number): Live | null {
  const [state, setState] = useState<Delayed>({ shown: null, held: [] })

  // Layout effects, so data that is due right away is shown without a frame of waiting
  useLayoutEffect(() => {
    if (!live) return
    setState((current) => {
      if (!current.shown) return { shown: live, held: [] }
      if (current.shown === live || current.held.some((item) => item.live === live)) return current
      return { ...current, held: [...current.held, { live, arrived: Date.now() }] }
    })
  }, [live])

  useLayoutEffect(() => {
    const first = state.held[0]
    if (!first) return
    const wait = dueAt(first, delayMs) - Date.now()
    if (wait <= 0) {
      setState((current) => releaseDue(current, delayMs))
      return
    }
    const timer = setTimeout(() => setState((current) => releaseDue(current, delayMs)), wait)
    return () => clearTimeout(timer)
  }, [state, delayMs])

  return state.shown
}

function SettingsPanel({ settings, onChange }: { settings: BoardSettings; onChange: (settings: BoardSettings) => void }) {
  /**
   * What is being typed. It only counts once done (Enter or leaving the field): on the way from 30 to 45
   * the field reads 4 for a moment, and held back goals would show up early.
   */
  const [typed, setTyped] = useState<string | null>(null)
  const setSeconds = (seconds: number) => {
    if (Number.isFinite(seconds)) onChange({ ...settings, delaySeconds: Math.min(MAX_DELAY_SECONDS, Math.max(0, Math.round(seconds))) })
  }
  const commit = () => {
    if (typed !== null && typed.trim() !== "") setSeconds(Number(typed.replace(",", ".")))
    setTyped(null)
  }
  return (
    <div className="lb-settings" role="group" aria-label="Einstellungen">
      <section className="lb-settings-section">
        <label className="lb-settings-check">
          <input type="checkbox" checked={settings.delay} onChange={(event) => onChange({ ...settings, delay: event.target.checked })} />
          Verzögerung
        </label>
        <div className={cn("lb-settings-seconds", !settings.delay && "lb-settings-off")}>
          <button
            type="button"
            className="lb-settings-step"
            disabled={!settings.delay || settings.delaySeconds <= 0}
            onClick={() => setSeconds(settings.delaySeconds - DELAY_STEP_SECONDS)}
            aria-label={`${DELAY_STEP_SECONDS} Sekunden weniger`}
          >
            −
          </button>
          <input
            type="text"
            inputMode="numeric"
            aria-label="Verzögerung in Sekunden"
            value={typed ?? String(settings.delaySeconds)}
            disabled={!settings.delay}
            onFocus={(event) => {
              setTyped(String(settings.delaySeconds))
              event.currentTarget.select()
            }}
            onChange={(event) => setTyped(event.target.value.replace(/[^\d,.]/g, ""))}
            onBlur={commit}
            onKeyDown={(event) => {
              if (event.key === "Enter") event.currentTarget.blur()
            }}
          />
          <button
            type="button"
            className="lb-settings-step"
            disabled={!settings.delay || settings.delaySeconds >= MAX_DELAY_SECONDS}
            onClick={() => setSeconds(settings.delaySeconds + DELAY_STEP_SECONDS)}
            aria-label={`${DELAY_STEP_SECONDS} Sekunden mehr`}
          >
            +
          </button>
          <span>Sekunden</span>
        </div>
        <p className="lb-settings-hint">Alle Punkte erscheinen N Sekunden später, damit das Board nicht spoilert.</p>
      </section>
      <section className="lb-settings-section">
        <h3 className="lb-settings-title">Große Animation bei</h3>
        <div className="lb-settings-kinds">
          {FLASH_OPTIONS.map((option) => (
            <label key={option.kind} className={cn("lb-settings-check lb-settings-kind", option.kind === "points" && "lb-settings-wide")}>
              <input
                type="checkbox"
                checked={settings.flash[option.kind]}
                onChange={(event) => onChange({ ...settings, flash: { ...settings.flash, [option.kind]: event.target.checked } })}
              />
              {option.mark && <EventMark kind={option.mark} />}
              {option.label}
            </label>
          ))}
        </div>
        <p className="lb-settings-hint">Alles andere zählt klein auf dem Spieler hoch.</p>
      </section>
    </div>
  )
}

// ---------------------------------------------------------------------------
// The engine: plays the moments one after another

type Pin = { shown: number; chip: number; row: number }
/** The data the board shows, and the players still held at their old points */
type View = { live: Live | null; pins: Record<string, Pin> }
type Flash = { moment: Moment; leaving: boolean }
type Flight = { id: string; x: number; y: number; dx: number; dy: number; points: number }
type Engine = ReturnType<typeof useBoardEngine>

function sleep(ms: number, signal: AbortSignal) {
  return new Promise<void>((resolve, reject) => {
    if (signal.aborted) return reject(signal.reason)
    const stop = () => {
      clearTimeout(timer)
      reject(signal.reason)
    }
    const timer = setTimeout(() => {
      signal.removeEventListener("abort", stop)
      resolve()
    }, ms)
    signal.addEventListener("abort", stop, { once: true })
  })
}

/**
 * Turns new live data into moments and plays them. Until a moment played, its player is "pinned": the
 * board shows the old points and keeps the old order. A pin moves to the new points in three stages,
 * the numbers first, then the player's place in the eleven, then the manager's place in the table.
 *
 * The board draws `view.live`, not the incoming data: new data is only taken over together with its pins,
 * so no render ever shows the new points in the new order before their moment played.
 *
 * `flashKinds` are the kinds of moments that get the flash. A change applies to the next update, without
 * interrupting what plays.
 */
function useBoardEngine(live: Live | null, key: string, root: RefObject<HTMLElement | null>, flashKinds: ReadonlySet<MomentKind>) {
  const kinds = useRef(flashKinds)
  // Declared first, so the effect below already plans with the current choice
  useLayoutEffect(() => {
    kinds.current = flashKinds
  })
  const [view, setView] = useState<View>({ live: null, pins: {} })
  const [flash, setFlash] = useState<Flash | null>(null)
  const [badges, setBadges] = useState<Record<string, number>>({})
  const [flights, setFlights] = useState<Flight[]>([])
  /** Managers whose row lights up while their points come in: 1 for gains, -1 for losses */
  const [lit, setLit] = useState<Record<string, number>>({})
  const [idle, setIdle] = useState(true)
  const queue = useRef<Step[]>([])
  const last = useRef<{ key: string; live: Live } | null>(null)
  const wake = useRef<(() => void) | null>(null)

  // A layout effect, so new data and its pins are in place before anything is painted
  useLayoutEffect(() => {
    if (!live) return
    const previous = last.current
    if (previous?.live === live && previous.key === key) return
    last.current = { key, live }
    if (!previous || previous.key !== key || previous.live.day !== live.day) {
      queue.current = []
      setView({ live, pins: {} })
      setFlash(null)
      setBadges({})
      setFlights([])
      setLit({})
      return
    }
    const moments = diffLive(previous.live, live)
    setView((current) => {
      const pins = { ...current.pins }
      for (const moment of moments) pins[moment.player.id] ??= { shown: moment.from, chip: moment.from, row: moment.from }
      return { live, pins }
    })
    if (!moments.length) return
    queue.current.push(...planSteps(moments, kinds.current))
    setIdle(false)
    wake.current?.()
  }, [live, key])

  useEffect(() => {
    const controller = new AbortController()
    const signal = controller.signal

    const advance = (moments: Moment[], stage: keyof Pin) =>
      setView((current) => {
        const pins = { ...current.pins }
        for (const moment of moments) if (pins[moment.player.id]) pins[moment.player.id] = { ...pins[moment.player.id], [stage]: moment.to }
        return { ...current, pins }
      })

    const launch = (moment: Moment) => {
      const node = root.current
      const source = node?.querySelector("[data-flash-points]")?.getBoundingClientRect()
      if (!node || !source) return
      const x = source.left + source.width / 2
      const y = source.top + source.height / 2
      setFlights(
        moment.managerIds.flatMap((managerId) => {
          const target = node.querySelector(`[data-score="${CSS.escape(`${managerId}:${moment.player.id}`)}"]`)?.getBoundingClientRect()
          if (!target) return []
          const dx = target.left + target.width / 2 - x
          const dy = target.top + target.height / 2 - y
          return [{ id: `${moment.id}:${managerId}`, x, y, dx, dy, points: moment.points }]
        }),
      )
    }

    /**
     * Glides the list to where the points are headed: back to the top when one of the managers is
     * among the first rows, otherwise to the best placed of them.
     */
    const reveal = (managerIds: string[]) => {
      const list = root.current?.querySelector<HTMLElement>(".lb-list")
      if (!list) return
      const rows = managerIds
        .map((id) => list.querySelector<HTMLElement>(`[data-flip="${CSS.escape(`row:${id}`)}"]`))
        .filter((row): row is HTMLElement => row !== null)
        .sort((a, b) => a.offsetTop - b.offsetTop)
      if (!rows.length) return
      const atTop = rows[0].offsetTop + rows[0].offsetHeight <= list.clientHeight
      const top = atTop ? 0 : rows[0].offsetTop - (list.clientHeight - rows[0].offsetHeight) / 2
      if (Math.abs(list.scrollTop - top) > 2) list.scrollTo({ top, behavior: "smooth" })
    }

    /** The top of the table is the board's home, back there once a moment further down played */
    const home = () => {
      const list = root.current?.querySelector<HTMLElement>(".lb-list")
      if (list && list.scrollTop > 2) list.scrollTo({ top: 0, behavior: "smooth" })
    }

    const light = (moments: Moment[]) => {
      const sums: Record<string, number> = {}
      for (const moment of moments) for (const id of moment.managerIds) sums[id] = (sums[id] ?? 0) + moment.points
      setLit(Object.fromEntries(Object.entries(sums).map(([id, points]) => [id, points < 0 ? -1 : 1])))
    }

    const playFlash = async (moment: Moment) => {
      setFlash({ moment, leaving: false })
      await sleep(FLASH_MS - REVEAL_MS, signal)
      reveal(moment.managerIds)
      await sleep(REVEAL_MS, signal)
      setFlash({ moment, leaving: true })
      light([moment])
      launch(moment)
      await sleep(FLIGHT_MS - 120, signal)
      advance([moment], "shown")
      await sleep(MANAGER_COUNT_MS, signal)
      setFlash(null)
      setFlights([])
      advance([moment], "chip")
      await sleep(CHIP_MOVE_MS * 0.6, signal)
      advance([moment], "row")
      await sleep(ROW_MOVE_MS + 300, signal)
      setLit({})
      home()
    }

    const playBadges = async (moments: Moment[]) => {
      setBadges(Object.fromEntries(moments.map((moment) => [moment.player.id, moment.points])))
      light(moments)
      advance(moments, "shown")
      await sleep(BADGE_MS, signal)
      setBadges({})
      advance(moments, "chip")
      await sleep(CHIP_MOVE_MS * 0.6, signal)
      advance(moments, "row")
      await sleep(ROW_MOVE_MS + 300, signal)
      setLit({})
    }

    const nextStep = () =>
      new Promise<void>((resolve, reject) => {
        const stop = () => reject(signal.reason)
        signal.addEventListener("abort", stop, { once: true })
        wake.current = () => {
          signal.removeEventListener("abort", stop)
          wake.current = null
          resolve()
        }
      })

    ;(async () => {
      try {
        for (;;) {
          const step = queue.current.shift()
          if (!step) {
            // Everything played, so every pin has reached the current points
            setIdle(true)
            setView((current) => (Object.keys(current.pins).length ? { ...current, pins: {} } : current))
            await nextStep()
            continue
          }
          setIdle(false)
          if (step.type === "flash") await playFlash(step.moment)
          else await playBadges(step.moments)
        }
      } catch {
        // Stopped: the board closed, or switched between live and demo
      }
    })()

    return () => {
      controller.abort()
      wake.current = null
      setFlash(null)
      setBadges({})
      setFlights([])
      setLit({})
    }
  }, [key, root])

  return { view, flash, badges, flights, lit, idle }
}

// ---------------------------------------------------------------------------
// The demo

/** Made-up moments on top of the real lineups, the next one as soon as the board played the last */
function useDemo(enabled: boolean, live: Live | undefined, idle: boolean): Live | null {
  const [state, setState] = useState<{ start: Live; live: Live; startedAt: number; steps: number } | null>(null)

  useEffect(() => {
    if (!enabled) setState(null)
    else if (live) {
      setState((current) => {
        if (current) return current
        const start = startDemo(live)
        return { start, live: start, startedAt: Date.now(), steps: 0 }
      })
    }
  }, [enabled, live])

  useEffect(() => {
    if (!state || !idle) return
    // A big moment first, then every fourth
    const timer = setTimeout(
      () =>
        setState(
          (current) =>
            current && {
              ...current,
              live: demoStep(current.live, current.start, current.steps % 4 === 0, current.startedAt),
              steps: current.steps + 1,
            },
        ),
      state.steps === 0 ? 1200 : 2400,
    )
    return () => clearTimeout(timer)
  }, [state, idle])

  return state?.live ?? null
}

// ---------------------------------------------------------------------------
// The board

type ChipModel = { player: LivePlayer; shown: number; sort: number; group: number; kickoff: string | null }
type RowModel = { manager: LiveManager; shown: number; sort: number; chips: ChipModel[] }

/** Managers and their players in the order the board shows right now, pinned players at their old points */
function boardRows(live: Live, pins: Record<string, Pin>): RowModel[] {
  const kickoffs = new Map<string, string>()
  for (const match of live.matches) {
    if (!match.kickoff) continue
    if (match.team1Id) kickoffs.set(match.team1Id, match.kickoff)
    if (match.team2Id) kickoffs.set(match.team2Id, match.kickoff)
  }
  return live.managers
    .map((manager) => {
      let shownOffset = 0
      let rowOffset = 0
      const chips = manager.players.map((player): ChipModel => {
        const pin = pins[player.id]
        if (pin) {
          shownOffset += player.points - pin.shown
          rowOffset += player.points - pin.row
        }
        return {
          player,
          shown: pin?.shown ?? player.points,
          sort: pin?.chip ?? player.points,
          // On the pitch first, then those done, then those still to play
          group: player.onField ? 0 : player.matchState === "upcoming" ? 2 : 1,
          kickoff: player.teamId ? (kickoffs.get(player.teamId) ?? null) : null,
        }
      })
      chips.sort(
        (a, b) =>
          a.group - b.group ||
          (a.group === 2 ? (a.kickoff ?? "").localeCompare(b.kickoff ?? "") : b.sort - a.sort) ||
          a.player.position - b.player.position,
      )
      return { manager, shown: manager.matchdayPoints - shownOffset, sort: manager.matchdayPoints - rowOffset, chips }
    })
    .sort((a, b) => b.sort - a.sort)
}

function Board({
  live,
  sourceKey,
  demo,
  leagueName,
  engine,
  picked,
  onPick,
  onOpenPlayer,
  lag,
}: {
  live: Live
  sourceKey: string
  demo: boolean
  leagueName: string
  engine: Engine
  picked: string | null
  onPick: (id: string) => void
  onOpenPlayer: (id: string) => void
  /** How far the board runs behind, in milliseconds */
  lag: number
}) {
  const list = useRef<HTMLDivElement>(null)
  const rows = useMemo(() => boardRows(live, engine.view.pins), [live, engine.view.pins])
  const matches = useMemo(() => boardMatches(live, picked), [live, picked])
  const managers = useMemo(() => new Map(live.managers.map((manager) => [manager.id, manager])), [live.managers])
  const rowHeight = useRowHeight(list, rows.length, sourceKey)
  // Rows moving because the screen or the number of rows changed are not worth a slide
  useFlip(list, `${sourceKey}:${rowHeight}:${rows.length}`)

  // Back to the top of the table once things calmed down
  useEffect(() => {
    if (!engine.idle) return
    const timer = setTimeout(() => list.current?.scrollTo({ top: 0, behavior: "smooth" }), 8_000)
    return () => clearTimeout(timer)
  }, [engine.idle])

  return (
    <>
      <section className="lb-hero">
        <Scoreboard live={live} matches={matches} lag={lag} />
        {engine.flash && <FlashLayer key={engine.flash.moment.id} flash={engine.flash} managers={managers} />}
      </section>
      {matches.parallel.length > 0 && (
        <nav
          className="lb-parallel"
          aria-label="Weitere laufende Spiele"
          data-rows={matches.parallel.length > PARALLEL_PER_ROW ? 2 : 1}
          style={{ "--cols": parallelColumns(matches.parallel.length) } as CSSProperties}
        >
          {matches.parallel.map((match) => (
            <button key={match.id} type="button" className="lb-parallel-match" onClick={() => onPick(match.id)} title="Groß anzeigen">
              <span className="lb-parallel-logo">
                <TeamLogo teamId={match.team1Id} size={120} />
              </span>
              <span className="lb-parallel-center">
                {/* A goal pops the digit, as on the big scoreboard */}
                <span className="lb-parallel-score">
                  <span key={`1-${match.team1Goals}`} className="lb-digit">
                    {match.team1Goals ?? 0}
                  </span>
                  <span className="lb-parallel-separator">:</span>
                  <span key={`2-${match.team2Goals}`} className="lb-digit">
                    {match.team2Goals ?? 0}
                  </span>
                </span>
                <ParallelClock match={match} updatedAt={live.updatedAt} lag={lag} />
              </span>
              <span className="lb-parallel-logo lb-parallel-logo-away">
                <TeamLogo teamId={match.team2Id} size={120} />
              </span>
            </button>
          ))}
        </nav>
      )}
      <div className="lb-band">
        <span className="lb-band-side">{live.day ? `${live.day}. Spieltag` : "Spieltag"}</span>
        <span className="lb-band-live">
          {(demo || matches.featured) && <i aria-hidden />}
          {demo ? "Demo" : matches.featured ? "Live" : "Live-Punkte"}
        </span>
        <span className="lb-band-side lb-band-right">{leagueName}</span>
      </div>
      <div ref={list} key={sourceKey} className="lb-list" style={{ "--row-h": `${rowHeight}px` } as CSSProperties}>
        {rows.map((row, index) => (
          <ManagerRow
            key={row.manager.id}
            row={row}
            rank={index + 1}
            badges={engine.badges}
            lit={engine.lit[row.manager.id]}
            onOpenPlayer={onOpenPlayer}
          />
        ))}
        {rows.length === 0 && <p className="lb-message">Noch keine Aufstellungen für diesen Spieltag.</p>}
      </div>
    </>
  )
}

/**
 * Show VISIBLE_ROWS managers on the screen, scroll down to see the rest
 */
function useRowHeight(list: RefObject<HTMLElement | null>, count: number, resetKey: string) {
  const [height, setHeight] = useState(110)
  // The list is a new element after switching between live and demo, so it is observed anew
  useLayoutEffect(() => {
    const node = list.current
    if (!node) return
    const measure = () => {
      if (!node.isConnected) return
      const rows = Math.min(Math.max(count, 1), VISIBLE_ROWS)
      const gap = 8
      const available = node.clientHeight - 16 - gap * (rows - 1)
      setHeight(Math.round(Math.min(170, Math.max(64, available / rows))))
    }
    measure()
    const observer = new ResizeObserver(measure)
    observer.observe(node)
    return () => observer.disconnect()
  }, [list, count, resetKey])
  return height
}

/**
 * Slides rows and players from where they were to where they are after a render (FLIP). Positions are
 * read from offsetLeft/offsetTop, which a running slide does not change. When `layoutKey` changes, or
 * the window is resized, positions are only noted, nothing slides.
 */
function useFlip(container: RefObject<HTMLElement | null>, layoutKey: string) {
  const positions = useRef(new Map<string, { x: number; y: number }>())
  const lastKey = useRef(layoutKey)
  const timers = useRef(new Set<number>())
  const counter = useRef(0)

  useEffect(() => {
    const forget = () => positions.current.clear()
    window.addEventListener("resize", forget)
    const pending = timers.current
    return () => {
      window.removeEventListener("resize", forget)
      pending.forEach(clearTimeout)
    }
  }, [])

  // Runs after every render. No cleanup: a slide that started finishes even when the board renders again.
  useLayoutEffect(() => {
    const node = container.current
    if (!node) return
    const items = [...node.querySelectorAll<HTMLElement>("[data-flip]")]
    const before = positions.current
    const after = new Map(items.map((item) => [item.dataset.flip!, { x: item.offsetLeft, y: item.offsetTop }]))
    positions.current = after
    if (lastKey.current !== layoutKey) {
      lastKey.current = layoutKey
      return
    }
    const moved: { item: HTMLElement; dx: number; dy: number }[] = []
    for (const item of items) {
      const from = before.get(item.dataset.flip!)
      const to = after.get(item.dataset.flip!)!
      if (!from) continue
      const dx = from.x - to.x
      const dy = from.y - to.y
      if (Math.abs(dx) >= 1 || Math.abs(dy) >= 1) moved.push({ item, dx, dy })
    }
    if (!moved.length) return
    // Each element remembers its latest slide, so an older slide's clean-up leaves a newer one alone
    const token = String(++counter.current)
    for (const { item, dx, dy } of moved) {
      item.dataset.flipToken = token
      item.style.transition = "none"
      item.style.transform = `translate3d(${dx}px, ${dy}px, 0)`
      // Its own layer while it moves, so the slide does not repaint the board
      item.style.willChange = "transform"
    }
    node.getBoundingClientRect()
    requestAnimationFrame(() => {
      for (const { item, dy } of moved) {
        if (item.dataset.flipToken !== token) continue
        const row = item.dataset.flip!.startsWith("row:")
        item.style.transition = `transform ${row ? ROW_MOVE_MS : CHIP_MOVE_MS}ms ${MOVE_EASE}, box-shadow 500ms ease`
        item.style.transform = ""
        // Rows climbing the table glow and stay on top while they pass the others
        if (row && dy > 0) item.dataset.rising = ""
      }
    })
    const timer = window.setTimeout(() => {
      timers.current.delete(timer)
      for (const { item } of moved) {
        if (item.dataset.flipToken !== token) continue
        item.style.transition = ""
        item.style.willChange = ""
        delete item.dataset.rising
        delete item.dataset.flipToken
      }
    }, Math.max(ROW_MOVE_MS, CHIP_MOVE_MS) + 100)
    timers.current.add(timer)
  })
}

function ManagerRow({
  row,
  rank,
  badges,
  lit,
  onOpenPlayer,
}: {
  row: RowModel
  rank: number
  badges: Record<string, number>
  lit: number | undefined
  onOpenPlayer: (id: string) => void
}) {
  const { manager } = row
  // The glow fades out in the color it had, so the last direction is kept after it ends
  const [tone, setTone] = useState(1)
  if (lit !== undefined && lit !== tone) setTone(lit)
  return (
    <article
      data-flip={`row:${manager.id}`}
      className={cn(
        "lb-row",
        tone < 0 && "lb-row-tone-down",
        lit !== undefined && "lb-row-lit",
        manager.isSelf && "lb-row-self",
        rank <= 3 && `lb-rank-${rank}`,
      )}
    >
      <strong className="lb-row-rank">{rank}</strong>
      <div className="lb-row-photo">
        <ManagerPhoto name={manager.name} image={manager.image} />
      </div>
      <div className="lb-row-info">
        <span className="lb-row-name">
          {manager.name}
          {manager.isSelf && <em className="lb-row-you">Du</em>}
        </span>
        <Count className="lb-row-total" value={row.shown} duration={MANAGER_COUNT_MS} />
        <span className="lb-row-status">
          {manager.playersStarted}/{manager.lineupSize} gespielt
          {manager.playersOnField > 0 && (
            <span className="lb-row-onfield">
              <i aria-hidden />
              {manager.playersOnField}
            </span>
          )}
        </span>
      </div>
      <div className="lb-track">
        {row.chips.map((chip) => (
          <PlayerChip key={chip.player.id} chip={chip} managerId={manager.id} badge={badges[chip.player.id]} onOpen={onOpenPlayer} />
        ))}
        {row.chips.length === 0 && <span className="lb-track-empty">Keine Aufstellung</span>}
      </div>
    </article>
  )
}

function PlayerChip({
  chip,
  managerId,
  badge,
  onOpen,
}: {
  chip: ChipModel
  managerId: string
  badge: number | undefined
  onOpen: (id: string) => void
}) {
  const { player } = chip
  const wide = player.onField
  const upcoming = player.matchState === "upcoming"
  const score = (
    <Count
      className="lb-chip-points"
      value={chip.shown}
      duration={badge === undefined ? PLAYER_COUNT_MS : BADGE_MS - 600}
      delay={badge === undefined ? 0 : 300}
      data-score={`${managerId}:${player.id}`}
    />
  )
  return (
    <div
      data-flip={`chip:${managerId}:${player.id}`}
      title={`${playerName(player)}: ${number(chip.shown)} Punkte`}
      role="button"
      tabIndex={0}
      aria-haspopup="dialog"
      onClick={() => onOpen(player.id)}
      onKeyDown={(event) => {
        if (event.key !== "Enter" && event.key !== " ") return
        event.preventDefault()
        onOpen(player.id)
      }}
      className={cn(
        "lb-chip",
        wide ? "lb-chip-wide" : "lb-chip-compact",
        upcoming && "lb-chip-upcoming",
        badge !== undefined && (badge < 0 ? "lb-chip-hit-down" : "lb-chip-hit-up"),
      )}
      style={{ "--grade": upcoming ? "transparent" : pointsGrade(chip.shown).fill } as CSSProperties}
    >
      <div className="lb-chip-photo">
        <Cutout image={player.image} teamId={player.teamId} className="lb-chip-img" />
        {badge !== undefined && <span className="lb-chip-badge">{signedNumber(badge)}</span>}
      </div>
      {wide ? (
        <div className="lb-chip-meta">
          <span className="lb-chip-name">{player.lastName}</span>
          {score}
          <Marks player={player} />
        </div>
      ) : (
        <div className="lb-chip-foot">{upcoming && chip.kickoff ? <span className="lb-chip-kickoff">{kickoffLabel(chip.kickoff)}</span> : score}</div>
      )}
    </div>
  )
}

/** Short enough for a small tile: the time today, otherwise the weekday */
function kickoffLabel(kickoff: string) {
  const date = new Date(kickoff)
  return date.toDateString() === new Date().toDateString() ? time(date) : date.toLocaleDateString("de-DE", { weekday: "short" })
}

function Marks({ player }: { player: LivePlayer }) {
  const marks = [
    ...Array.from({ length: player.goals }, (_, i) => <span key={`g${i}`} aria-label="Tor">⚽</span>),
    ...Array.from({ length: player.assists }, (_, i) => (
      <span key={`a${i}`} className="lb-mark-assist" aria-label="Vorlage">
        A
      </span>
    )),
    ...Array.from({ length: player.yellowCards }, (_, i) => <span key={`y${i}`} className="lb-mark-card bg-yellow-400" aria-label="Gelbe Karte" />),
    ...Array.from({ length: player.yellowRedCards }, (_, i) => (
      <span key={`yr${i}`} className="lb-mark-card bg-linear-to-br from-yellow-400 from-50% to-red-500 to-50%" aria-label="Gelb-Rote Karte" />
    )),
    ...Array.from({ length: player.redCards }, (_, i) => <span key={`r${i}`} className="lb-mark-card bg-red-500" aria-label="Rote Karte" />),
  ]
  return marks.length ? <span className="lb-chip-marks">{marks}</span> : null
}

// ---------------------------------------------------------------------------
// A player's events

type EventOrder = "time" | "type"

/** Where the player is in their match */
function playerStatus(player: LivePlayer): string {
  const clock = player.matchMinute ? ` · ${player.matchMinute}'` : ""
  if (player.onField) return `Auf dem Platz${clock}`
  if (player.matchState === "running") {
    if (player.redCards + player.yellowRedCards > 0) return `Platzverweis${clock}`
    return player.role === "bench" ? `Auf der Bank${clock}` : `Live${clock}`
  }
  if (player.matchState === "finished") return player.role === "bench" ? "Nicht eingesetzt" : `Beendet${player.minute ? ` · ${player.minute} Min.` : ""}`
  return "Noch nicht gespielt"
}

const minuteLabel = (minute: number | null) => (minute === null ? "–" : `${minute}'`)

/**
 * Everything a player did so far: in the order of the match, the newest on top as in a live ticker,
 * or summed up per type, the most frequent first.
 */
function PlayerEvents({
  live,
  playerId,
  order,
  onOrder,
  onClose,
}: {
  live: Live
  playerId: string
  order: EventOrder
  onOrder: (order: EventOrder) => void
  onClose: () => void
}) {
  const teams = useTeamMap()
  const player = useMemo(() => live.managers.flatMap((manager) => manager.players).find((item) => item.id === playerId) ?? null, [live, playerId])
  if (!player) return null

  const timeline = player.timeline ?? []
  const newestFirst = [...timeline].reverse()
  // What each type of event is, and when it happened
  const kinds = new Map<string, LiveEventKind>()
  const minutes = new Map<string, (number | null)[]>()
  for (const event of timeline) {
    if (event.kind) kinds.set(event.name, event.kind)
    minutes.set(event.name, [...(minutes.get(event.name) ?? []), event.minute])
  }
  const byType = [...player.events].sort((a, b) => b.count - a.count || Math.abs(b.points) - Math.abs(a.points))
  const fieldedBy = live.managers.filter((manager) => manager.players.some((item) => item.id === playerId))
  const team = teams.get(player.teamId ?? "")

  return (
    <div className="lb-sheet-backdrop" onClick={onClose}>
      <section
        className="lb-sheet"
        role="dialog"
        aria-modal="true"
        aria-label={`Ereignisse von ${playerName(player)}`}
        onClick={(event) => event.stopPropagation()}
      >
        <header className="lb-sheet-head">
          <div className="lb-sheet-photo">
            <Cutout image={player.image} teamId={player.teamId} className="lb-chip-img" />
          </div>
          <div className="lb-sheet-who">
            <strong className="lb-sheet-name">{playerName(player)}</strong>
            <span className="lb-sheet-meta">
              <TeamLogo teamId={player.teamId} size={18} />
              <span className="lb-sheet-clip">{[team?.name, position(player.position).long].filter(Boolean).join(" · ")}</span>
            </span>
            <span className={cn("lb-sheet-meta", player.onField && "lb-sheet-onfield")}>
              {player.onField && <i aria-hidden />}
              {playerStatus(player)}
            </span>
          </div>
          <div className="lb-sheet-points">
            <strong className={cn(player.points < 0 && "lb-event-down")}>{number(player.points)}</strong>
            <span>Punkte</span>
          </div>
          <button type="button" onClick={onClose} className="lb-toolbar-button lb-sheet-close" aria-label="Schließen" autoFocus>
            <X className="size-4" />
          </button>
        </header>

        <div className="lb-sheet-tabs" role="tablist" aria-label="Sortierung">
          <button type="button" role="tab" aria-selected={order === "time"} onClick={() => onOrder("time")}>
            Chronologisch
          </button>
          <button type="button" role="tab" aria-selected={order === "type"} onClick={() => onOrder("type")}>
            Nach Ereignis
          </button>
        </div>

        {player.events.length === 0 ? (
          <p className="lb-sheet-empty">{player.matchState === "upcoming" ? "Das Spiel hat noch nicht begonnen." : "Noch keine Ereignisse."}</p>
        ) : order === "time" ? (
          timeline.length ? (
            <ol className="lb-sheet-list">
              {newestFirst.map((event, index) => (
                <li key={timeline.length - index} className={cn("lb-event", event.kind && "lb-event-marked")}>
                  {/* The minute once, on the first event of a minute */}
                  <span className="lb-event-lead">{index === 0 || newestFirst[index - 1].minute !== event.minute ? minuteLabel(event.minute) : ""}</span>
                  <span className="lb-event-name">
                    <EventMark kind={event.kind} />
                    <span className="lb-event-text">{event.name}</span>
                  </span>
                  <span className={cn("lb-event-points", event.points < 0 ? "lb-event-down" : "lb-event-up")}>{signedNumber(event.points)}</span>
                </li>
              ))}
            </ol>
          ) : (
            <p className="lb-sheet-empty">Für diesen Spieler sind keine Zeiten bekannt.</p>
          )
        ) : (
          <ol className="lb-sheet-list">
            {byType.map((event) => {
              const kind = kinds.get(event.name) ?? null
              const at = minutes.get(event.name) ?? []
              return (
                <li key={event.name} className={cn("lb-event", kind && "lb-event-marked")}>
                  <span className="lb-event-lead">{event.count}×</span>
                  <span className="lb-event-name">
                    <EventMark kind={kind} />
                    <span className="lb-event-text">
                      {event.name}
                      {at.length > 0 && <small>{at.map(minuteLabel).join(" · ")}</small>}
                    </span>
                  </span>
                  <span className={cn("lb-event-points", event.points < 0 ? "lb-event-down" : "lb-event-up")}>{signedNumber(event.points)}</span>
                </li>
              )
            })}
          </ol>
        )}

        {fieldedBy.length > 0 && <footer className="lb-sheet-foot">In der Startelf von {fieldedBy.map((manager) => manager.name).join(", ")}</footer>}
      </section>
    </div>
  )
}

/** Goals, assists and cards get their sign, as on the player tiles */
function EventMark({ kind }: { kind: LiveEventKind | null }) {
  switch (kind) {
    case "goal":
      return <span aria-label="Tor">⚽</span>
    case "own_goal":
      return <span className="lb-mark-own">ET</span>
    case "assist":
      return <span className="lb-mark-assist">A</span>
    case "yellow":
      return <span className="lb-mark-card bg-yellow-400" aria-label="Gelbe Karte" />
    case "yellow_red":
      return <span className="lb-mark-card bg-linear-to-br from-yellow-400 from-50% to-red-500 to-50%" aria-label="Gelb-Rote Karte" />
    case "red":
      return <span className="lb-mark-card bg-red-500" aria-label="Rote Karte" />
    default:
      return null
  }
}

// ---------------------------------------------------------------------------
// Scoreboard and flash

function Scoreboard({ live, matches, lag }: { live: Live; matches: ReturnType<typeof boardMatches>; lag: number }) {
  // The board's time: as far behind as its data, so the clock does not run ahead of the TV
  const now = useNow(1_000) - lag
  const teams = useTeamMap()
  const { featured, next } = matches

  if (featured) {
    return (
      <div className="lb-scoreboard">
        <TeamSide teamId={featured.team1Id} name={teams.get(featured.team1Id ?? "")?.name} />
        <div className="lb-score-center">
          <div className="lb-score">
            <span key={`1-${featured.team1Goals}`} className="lb-digit">
              {featured.team1Goals ?? 0}
            </span>
            <span className="lb-score-separator">:</span>
            <span key={`2-${featured.team2Goals}`} className="lb-digit">
              {featured.team2Goals ?? 0}
            </span>
          </div>
          <span className="lb-clock">
            <i aria-hidden />
            {matchClock(featured, live.updatedAt, now)}
          </span>
        </div>
        <TeamSide teamId={featured.team2Id} name={teams.get(featured.team2Id ?? "")?.name} />
      </div>
    )
  }

  if (next?.kickoff) {
    const left = new Date(next.kickoff).getTime() - now
    return (
      <div className="lb-scoreboard">
        <TeamSide teamId={next.team1Id} name={teams.get(next.team1Id ?? "")?.name} />
        <div className="lb-score-center">
          <span className="lb-eyebrow">Nächster Anstoß</span>
          <div className="lb-countdown">{left > 0 && left < 86_400_000 ? hms(left) : weekdayTime(next.kickoff)}</div>
          {left > 0 && left < 86_400_000 && <span className="lb-eyebrow lb-eyebrow-dim">{weekdayTime(next.kickoff)} Uhr</span>}
        </div>
        <TeamSide teamId={next.team2Id} name={teams.get(next.team2Id ?? "")?.name} />
      </div>
    )
  }

  const leader = live.managers.reduce<LiveManager | null>((best, manager) => (!best || manager.matchdayPoints > best.matchdayPoints ? manager : best), null)
  return (
    <div className="lb-scoreboard lb-scoreboard-single">
      <div className="lb-score-center">
        <span className="lb-eyebrow">{live.matches.length ? "Spieltag beendet" : "Kein Spiel"}</span>
        {leader && (
          <div className="lb-final">
            {leader.name} <span>{number(leader.matchdayPoints)} Punkte</span>
          </div>
        )}
      </div>
    </div>
  )
}

const hms = (ms: number) => {
  const seconds = Math.floor(ms / 1000)
  const pad = (value: number) => String(value).padStart(2, "0")
  return `${pad(Math.floor(seconds / 3600))}:${pad(Math.floor((seconds % 3600) / 60))}:${pad(seconds % 60)}`
}

function TeamSide({ teamId, name }: { teamId: string | null; name: string | undefined }) {
  return (
    <div className="lb-team">
      <div className="lb-team-logo">
        <TeamLogo teamId={teamId} size={160} />
      </div>
      <span className="lb-team-name">{name ?? ""}</span>
    </div>
  )
}

/** All in one row up to five matches, more share two rows */
const PARALLEL_PER_ROW = 5
const parallelColumns = (count: number) => (count <= PARALLEL_PER_ROW ? count : Math.ceil(count / 2))

function ParallelClock({ match, updatedAt, lag }: { match: Match; updatedAt: string; lag: number }) {
  const now = useNow(10_000) - lag
  return <span className="lb-parallel-clock">{matchClock(match, updatedAt, now)}</span>
}

/** Positions of the plus or minus signs bursting out of a flash: left, size, delay, rotation, drift and height */
const BURST = Array.from({ length: 20 }, (_, i) => {
  const wave = (i * 37) % 100
  return {
    x: `${(i * 53) % 96}%`,
    s: `${3.2 + ((i * 7) % 5) * 1.1}vh`,
    d: `${(i % 5) * 70 + Math.floor(i / 5) * 160}ms`,
    r: `${((i * 29) % 60) - 30}deg`,
    drift: `${((i * 41) % 120) - 60}px`,
    h: `${22 + (wave % 30)}vh`,
  }
})

function FlashLayer({ flash, managers }: { flash: Flash; managers: Map<string, LiveManager> }) {
  const { moment } = flash
  const negative = moment.points < 0
  const minute = Number.parseInt(moment.player.matchMinute ?? "", 10)
  return (
    <div
      className={cn(
        "lb-flash",
        negative ? "lb-flash-negative" : "lb-flash-positive",
        moment.kind === "goal" && "lb-flash-goal",
        flash.leaving && "lb-flash-leaving",
      )}
      role="status"
    >
      <div className="lb-flash-stripes" aria-hidden />
      <div className="lb-flash-burst" aria-hidden>
        {BURST.map((spark, i) => (
          <span
            key={i}
            style={{ "--x": spark.x, "--s": spark.s, "--d": spark.d, "--r": spark.r, "--drift": spark.drift, "--h": spark.h } as CSSProperties}
          >
            {negative ? "−" : "+"}
          </span>
        ))}
      </div>
      <div className="lb-flash-content">
        <div className="lb-flash-portrait">
          <div className="lb-flash-club">
            <TeamLogo teamId={moment.player.teamId} size={200} />
          </div>
          <Cutout image={moment.player.image} teamId={moment.player.teamId} className="lb-flash-player" />
          <div className="lb-flash-managers">
            {moment.managerIds.slice(0, 5).map((id) => {
              const manager = managers.get(id)
              return manager ? (
                <span key={id} className="lb-flash-manager" title={manager.name}>
                  <ManagerPhoto name={manager.name} image={manager.image} />
                </span>
              ) : null
            })}
            {moment.managerIds.length > 5 && <span className="lb-flash-manager lb-flash-more">+{moment.managerIds.length - 5}</span>}
          </div>
        </div>
        <div className="lb-flash-text">
          <strong className="lb-flash-name">{playerName(moment.player)}</strong>
          <strong className="lb-flash-action">{moment.action}</strong>
        </div>
        <div className="lb-flash-badges">
          {Number.isFinite(minute) && (
            <div className="lb-flash-circle lb-flash-minute">
              <strong>{minute}'</strong>
              <span>Minute</span>
            </div>
          )}
          <div className="lb-flash-circle lb-flash-points" data-flash-points>
            <strong>{signedNumber(moment.points)}</strong>
            <span>Punkte</span>
          </div>
        </div>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Small pieces

/**
 * A number that counts to its new value. The text is written directly, so the counting does not render
 * the board 60 times a second. While it counts it carries data-trend for the color and the pulse.
 */
function Count({
  value,
  duration,
  delay = 0,
  className,
  ...props
}: { value: number; duration: number; delay?: number; className?: string } & Record<`data-${string}`, string>) {
  const ref = useRef<HTMLSpanElement>(null)
  const shown = useRef(value)

  useLayoutEffect(() => {
    if (ref.current) ref.current.textContent = number(shown.current)
  }, [])

  useEffect(() => {
    const node = ref.current
    const from = shown.current
    if (!node || from === value) return
    node.dataset.trend = value > from ? "up" : "down"
    const start = performance.now()
    let frame = 0
    let timer = 0
    const tick = (now: number) => {
      const progress = Math.min(1, Math.max(0, (now - start - delay) / duration))
      shown.current = Math.round(from + (value - from) * (1 - (1 - progress) ** 3))
      node.textContent = number(shown.current)
      if (progress < 1) frame = requestAnimationFrame(tick)
      else timer = window.setTimeout(() => delete node.dataset.trend, 500)
    }
    frame = requestAnimationFrame(tick)
    return () => {
      cancelAnimationFrame(frame)
      clearTimeout(timer)
      delete node.dataset.trend
    }
  }, [value, duration, delay])

  return <span ref={ref} className={cn("lb-count", className)} {...props} />
}

/** A Kickbase cut-out, framed on head and shoulders. The club badge stands in when there is none. */
function Cutout({ image, teamId, className }: { image: string | null; teamId: string | null; className: string }) {
  const src = cdnUrl(image)
  const [failed, setFailed] = useState<string | null>(null)
  if (!src || failed === src) {
    return (
      <span className="lb-cutout-fallback">
        <TeamLogo teamId={teamId} size={48} />
      </span>
    )
  }
  return <img src={src} alt="" className={className} onError={() => setFailed(src)} />
}

/** Without a photo, the initials on a color of their own, the same for a manager every time */
function ManagerPhoto({ name, image }: { name: string; image: string | null }) {
  const src = cdnUrl(image)
  const [failed, setFailed] = useState<string | null>(null)
  if (!src || failed === src) {
    const hue = [...name].reduce((sum, char) => (sum * 31 + char.charCodeAt(0)) % 360, 7)
    return (
      <span className="lb-initials" style={{ "--hue": hue } as CSSProperties}>
        {initials(name)}
      </span>
    )
  }
  return <img src={src} alt="" onError={() => setFailed(src)} />
}

// ---------------------------------------------------------------------------
// Screen

function useFullscreen() {
  const [active, setActive] = useState(() => Boolean(document.fullscreenElement))
  useEffect(() => {
    const update = () => setActive(Boolean(document.fullscreenElement))
    document.addEventListener("fullscreenchange", update)
    return () => document.removeEventListener("fullscreenchange", update)
  }, [])
  const toggle = useCallback(() => {
    if (document.fullscreenElement) document.exitFullscreen().catch(() => {})
    else document.documentElement.requestFullscreen().catch(() => {})
  }, [])
  return { active, toggle, supported: document.fullscreenEnabled }
}

/** Whether the mouse moved recently. Without, the controls and the cursor fade out. */
function useRestless(root: RefObject<HTMLElement | null>) {
  const [restless, setRestless] = useState(true)
  useEffect(() => {
    const node = root.current
    if (!node) return
    let timer = setTimeout(() => setRestless(false), 3_000)
    const wake = () => {
      setRestless(true)
      clearTimeout(timer)
      timer = setTimeout(() => setRestless(false), 3_000)
    }
    node.addEventListener("pointermove", wake)
    node.addEventListener("pointerdown", wake)
    node.addEventListener("keydown", wake)
    return () => {
      clearTimeout(timer)
      node.removeEventListener("pointermove", wake)
      node.removeEventListener("pointerdown", wake)
      node.removeEventListener("keydown", wake)
    }
  }, [root])
  return restless
}

/** Keeps the screen on while the board is open, where the browser allows it */
function useWakeLock() {
  useEffect(() => {
    let lock: WakeLockSentinel | null = null
    let released = false
    const request = () => {
      if (document.visibilityState !== "visible" || !("wakeLock" in navigator)) return
      navigator.wakeLock
        .request("screen")
        .then((sentinel) => {
          if (released) sentinel.release().catch(() => {})
          else lock = sentinel
        })
        .catch(() => {})
    }
    request()
    document.addEventListener("visibilitychange", request)
    return () => {
      released = true
      document.removeEventListener("visibilitychange", request)
      lock?.release().catch(() => {})
    }
  }, [])
}
