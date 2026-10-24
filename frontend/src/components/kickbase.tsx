/**
 * Kickbase-related components such as team logos, avatars, position badges, and status icons.
*/

import {
  Ambulance,
  ArrowRightFromLine,
  Bandage,
  CheckCircle2,
  Clock,
  Construction,
  HelpCircle,
  Minus,
  Shield,
  Square,
  TrendingDown,
  TrendingUp,
} from "lucide-react"
import { type ReactNode, useState } from "react"
import { useTeamMap } from "@/api/hooks"
import { cn } from "@/lib/cn"
import { compactMoney, money, percent, signedMoney } from "@/lib/format"
import { cdnUrl, initials, playerName, position, status as statusMeta } from "@/lib/kickbase"

/**
 * The club's logo from Kickbase's CDN: its logo pool by team id, which needs no data to be loaded,
 * then the path the API sends, then a neutral shield.
 */
export function TeamLogo({ teamId, size = 24, className }: { teamId: string | null | undefined; size?: number; className?: string }) {
  const teams = useTeamMap()
  const team = teamId ? teams.get(teamId) : undefined
  const sources = [teamId && /^\d+$/.test(teamId) ? cdnUrl(`pool/teams/${teamId}.png`) : null, cdnUrl(team?.image)].filter(
    (src): src is string => Boolean(src),
  )
  const [failed, setFailed] = useState<string[]>([])
  const src = sources.find((candidate) => !failed.includes(candidate))
  if (!src) {
    return (
      <Shield
        aria-label={team?.name}
        strokeWidth={1.5}
        className={cn("shrink-0 text-muted", className)}
        style={{ width: size, height: size }}
      />
    )
  }
  return (
    <img
      src={src}
      alt={team?.name ?? ""}
      title={team?.name}
      width={size}
      height={size}
      loading="lazy"
      onError={() => setFailed((list) => (list.includes(src) ? list : [...list, src]))}
      className={cn("shrink-0 object-contain", className)}
      style={{ width: size, height: size }}
    />
  )
}

const AVATAR_TONES = [
  "bg-emerald-500/20 text-emerald-700 dark:text-emerald-300",
  "bg-sky-500/20 text-sky-700 dark:text-sky-300",
  "bg-amber-500/20 text-amber-700 dark:text-amber-300",
  "bg-rose-500/20 text-rose-700 dark:text-rose-300",
  "bg-violet-500/20 text-violet-700 dark:text-violet-300",
  "bg-cyan-500/20 text-cyan-700 dark:text-cyan-300",
]

export function Avatar({
  name,
  image,
  size = 32,
  className,
}: {
  name: string
  image?: string | null
  size?: number
  className?: string
}) {
  const [failed, setFailed] = useState(false)
  const src = cdnUrl(image)
  const tone = AVATAR_TONES[[...name].reduce((sum, c) => sum + c.charCodeAt(0), 0) % AVATAR_TONES.length]
  return (
    <span
      className={cn("inline-grid shrink-0 place-items-center overflow-hidden rounded-full font-semibold", tone, className)}
      style={{ width: size, height: size, fontSize: Math.max(10, size * 0.38) }}
    >
      {src && !failed ? (
        <img src={src} alt="" loading="lazy" onError={() => setFailed(true)} className="size-full object-cover" />
      ) : (
        initials(name)
      )}
    </span>
  )
}

export function PositionBadge({ value, className }: { value: number | null | undefined; className?: string }) {
  const meta = position(value)
  return (
    <span
      title={meta.long}
      className={cn(
        "inline-flex h-5 min-w-9 items-center justify-center rounded-md px-1.5 text-[10px] font-bold tracking-wide",
        meta.tone,
        className,
      )}
    >
      {meta.short}
    </span>
  )
}

export function StatusIcon({ value, text, className }: { value: number; text?: string | null; className?: string }) {
  const meta = statusMeta(value)
  const title = text ? `${meta.label}: ${text}` : meta.label
  const props = { className: cn("size-4 shrink-0", className), "aria-label": title }
  const icon = (() => {
    switch (meta.kind) {
      case "fit":
        return <CheckCircle2 {...props} className={cn(props.className, "text-up")} />
      case "injured":
        return <Ambulance {...props} className={cn(props.className, "text-down")} />
      case "doubtful":
        return <Bandage {...props} className={cn(props.className, "text-orange-500")} />
      case "rehab":
        return <Construction {...props} className={cn(props.className, "text-amber-500")} />
      case "red":
        return <Square {...props} className={cn(props.className, "fill-red-500 text-red-500")} />
      case "yellowRed":
        return <Square {...props} className={cn(props.className, "fill-orange-500 text-orange-500")} />
      case "yellow":
        return <Square {...props} className={cn(props.className, "fill-yellow-400 text-yellow-400")} />
      case "left":
        return <ArrowRightFromLine {...props} className={cn(props.className, "text-down")} />
      case "absent":
        return <Clock {...props} className={cn(props.className, "text-muted")} />
      default:
        return <HelpCircle {...props} className={cn(props.className, "text-muted")} />
    }
  })()
  return (
    <span title={title} className="inline-flex">
      {icon}
    </span>
  )
}

/** A status icon only when the player is not fit, so tables stay calm */
export function StatusFlag({ value, text }: { value: number; text?: string | null }) {
  return value === 0 ? null : <StatusIcon value={value} text={text} />
}

export function TrendIcon({ value, className }: { value: number; className?: string }) {
  if (value === 1) return <TrendingUp aria-label="steigend" className={cn("size-4 text-up", className)} />
  if (value === 2) return <TrendingDown aria-label="fallend" className={cn("size-4 text-down", className)} />
  return <Minus aria-label="gleichbleibend" className={cn("size-4 text-muted", className)} />
}

/** A colored money delta. Missing history shows a dash, never a misleading zero. */
export function Delta({ value, compact, className }: { value: number | null | undefined; compact?: boolean; className?: string }) {
  return (
    <span
      className={cn(
        "tabular-nums",
        value == null || value === 0 ? "text-muted" : value > 0 ? "text-up" : "text-down",
        className,
      )}
    >
      {signedMoney(value, compact)}
    </span>
  )
}

export function PercentDelta({ value, className, invert }: { value: number | null | undefined; className?: string; invert?: boolean }) {
  const good = value != null && (invert ? value < 0 : value > 0)
  const bad = value != null && (invert ? value > 0 : value < 0)
  return <span className={cn("tabular-nums", good && "text-up", bad && "text-down", !good && !bad && "text-muted", className)}>{percent(value)}</span>
}

/** Full amount on wide screens, compact on narrow ones */
export function Money({ value, className }: { value: number | null | undefined; className?: string }) {
  return (
    <span className={cn("tabular-nums whitespace-nowrap", className)}>
      <span className="hidden 3xl:inline">{money(value)}</span>
      <span className="3xl:hidden" title={money(value)}>
        {compactMoney(value)}
      </span>
    </span>
  )
}

/**
 * A player's portrait, cropped to head and shoulders, with the club badge in the corner.
 *
 * Kickbase's pictures are 1100 x 800 cut-outs with the head in the upper middle. Scaled to 165% of
 * the avatar's height and shifted up a little, the head and collar fill the circle. Without a picture
 * the club badge stands in.
 */
export function PlayerAvatar({
  image,
  teamId,
  size = 36,
  rounded = "full",
  badge = true,
  className,
}: {
  image?: string | null
  teamId: string | null
  size?: number
  rounded?: "full" | "xl"
  badge?: boolean
  className?: string
}) {
  const [failed, setFailed] = useState<string | null>(null)
  const src = cdnUrl(image)
  const showPhoto = src !== null && failed !== src
  return (
    <span className={cn("relative inline-block shrink-0", className)} style={{ width: size, height: size }}>
      <span
        className={cn(
          "absolute inset-0 overflow-hidden bg-gradient-to-b from-surface-2 to-surface-3",
          rounded === "full" ? "rounded-full" : "rounded-2xl",
        )}
      >
        {showPhoto ? (
          <img
            src={src}
            alt=""
            loading="lazy"
            onError={() => setFailed(src)}
            className="absolute left-1/2 max-w-none -translate-x-1/2"
            style={{ height: size * 1.65, top: -size * 0.13 }}
          />
        ) : (
          <span className="grid size-full place-items-center">
            <TeamLogo teamId={teamId} size={Math.round(size * 0.62)} />
          </span>
        )}
      </span>
      {badge && showPhoto && teamId && (
        <span
          className="absolute -right-1 -bottom-1 grid place-items-center rounded-full bg-surface ring-2 ring-surface"
          style={{ width: size * 0.46, height: size * 0.46 }}
        >
          <TeamLogo teamId={teamId} size={Math.round(size * 0.38)} />
        </span>
      )}
    </span>
  )
}

export function PlayerCell({
  player,
  sub,
  className,
  size = 36,
}: {
  player: {
    firstName?: string | null
    lastName: string
    teamId: string | null
    image?: string | null
    position: number
    status: number
    statusText?: string | null
  }
  sub?: ReactNode
  className?: string
  size?: number
}) {
  return (
    <div className={cn("flex min-w-0 items-center gap-3", className)}>
      <PlayerAvatar image={player.image} teamId={player.teamId} size={size} />
      <div className="min-w-0">
        <div className="flex items-center gap-1.5">
          <span className="truncate font-medium">{playerName(player)}</span>
          <StatusFlag value={player.status} text={player.statusText} />
        </div>
        <div className="mt-0.5 flex items-center gap-1.5 text-xs text-muted">
          <PositionBadge value={player.position} />
          {sub}
        </div>
      </div>
    </div>
  )
}

/** App Logo */
export function KickbaseMark({ className = "size-8" }: { className?: string }) {
  return <img src="/favicon.png" alt="" width={48} height={48} className={cn("shrink-0 rounded-xl", className)} />
}

