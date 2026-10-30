import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { AnimatePresence, motion } from 'motion/react'
import {
  AlertTriangle,
  Loader2,
  LogOut,
  Mic,
  MicOff,
  Pencil,
  Shield,
  Square,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Robot, type RobotMood } from '@/components/robot'
import { Waveform } from '@/components/waveform'
import { Wordmark } from '@/components/site/wordmark'
import { FormError } from '@/components/site/form-error'
import { UsageMeter } from '@/components/usage-meter'
import { useMe } from '@/hooks/use-me'
import { useVoiceSession, type VoiceState } from '@/hooks/use-voice-session'
import { api, checkWakeName } from '@/lib/api'
import { cn } from '@/lib/utils'

const MOOD: Record<VoiceState, RobotMood> = {
  offline: 'idle',
  wake: 'idle',
  listening: 'listening',
  always_on: 'listening',
  thinking: 'thinking',
  speaking: 'speaking',
  error: 'error',
}

function stateLabel(state: VoiceState, wakeName: string) {
  switch (state) {
    case 'wake':
      return `Say "Hey ${wakeName}"`
    case 'listening':
      return 'Listening'
    case 'always_on':
      return 'Always listening'
    case 'thinking':
      return 'Thinking'
    case 'speaking':
      return 'Speaking'
    case 'error':
      return 'Reconnecting'
    default:
      return 'Connecting'
  }
}

export default function AssistantPage() {
  const { me, loading, countExchange, setWakeName } = useMe()
  const session = useVoiceSession({ onExchange: countExchange })
  const [renaming, setRenaming] = useState(false)

  const wakeName = me?.wake_name ?? 'Saira'

  useEffect(() => {
    document.title = `${wakeName} · voice assistant`
  }, [wakeName])

  const mood = MOOD[session.state]
  const busy = session.state === 'thinking' || session.state === 'speaking'

  if (loading) {
    return (
      <div className="grid min-h-dvh place-items-center">
        <Loader2 className="size-5 animate-spin text-brand" />
      </div>
    )
  }

  return (
    <div className="flex min-h-dvh flex-col">
      <header className="glass sticky top-0 z-40 border-b border-border">
        <div className="mx-auto flex h-14 max-w-7xl items-center gap-4 px-5">
          <Wordmark to="/app" />
          <span className="hidden text-sm text-muted-foreground sm:inline">
            {me?.display_name || me?.email}
          </span>

          <div className="ml-auto flex items-center gap-2 sm:gap-3">
            {me && <UsageMeter used={me.used} limit={me.limit} className="hidden sm:flex" />}
            {me?.role === 'admin' && (
              <Button variant="ghost" size="sm" asChild>
                <Link to="/admin">
                  <Shield className="size-3.5" />
                  Admin
                </Link>
              </Button>
            )}
            <Button
              variant="ghost"
              size="sm"
              onClick={async () => {
                await api.logout().catch(() => {})
                window.location.href = '/'
              }}
            >
              <LogOut className="size-3.5" />
              <span className="hidden sm:inline">Sign out</span>
            </Button>
          </div>
        </div>
      </header>

      <AnimatePresence>
        {session.quota && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden border-b border-destructive/40 bg-destructive/10"
          >
            <div className="mx-auto flex max-w-7xl items-center gap-2.5 px-5 py-3 text-sm text-destructive">
              <AlertTriangle className="size-4 shrink-0" />
              {session.quota}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <main className="mx-auto grid w-full max-w-7xl flex-1 gap-6 px-5 py-8 lg:grid-cols-[1fr_320px]">
        {/* ── Core ───────────────────────────────────────────────────────── */}
        <section className="flex flex-col items-center">
          <Robot mood={mood} className="w-44 sm:w-52" />

          <div className="mt-6 text-center">
            <h1 className="font-display text-xl font-bold tracking-[0.18em] uppercase">
              {wakeName}
            </h1>
            <button
              onClick={() => setRenaming(true)}
              className="mt-1.5 inline-flex items-center gap-1.5 text-xs text-muted-foreground transition-colors hover:text-brand"
            >
              <Pencil className="size-3" />
              Change the name
            </button>
          </div>

          <motion.div layout className="mt-5">
            <Badge
              variant="outline"
              className={cn(
                'gap-2 px-3 py-1 text-xs',
                session.state === 'error'
                  ? 'border-destructive/40 text-destructive'
                  : 'border-brand/35 text-brand',
              )}
            >
              <motion.span
                className="size-1.5 rounded-full bg-current"
                animate={busy ? { opacity: [1, 0.25, 1] } : { opacity: 1 }}
                transition={{ repeat: busy ? Infinity : 0, duration: 1 }}
              />
              {stateLabel(session.state, wakeName)}
            </Badge>
          </motion.div>

          <Waveform
            analyserRef={session.analyserRef}
            active={session.micStatus === 'active'}
            className="mt-6 h-20 w-full max-w-xl"
          />

          {/* Transcript / reply */}
          <div className="mt-2 grid w-full max-w-xl gap-3">
            <Panel
              tag="You said"
              active={!!session.transcript}
              text={session.transcript || 'Waiting for you to speak…'}
              muted={!session.transcript}
            />
            <Panel
              tag={`${wakeName} said`}
              active={!!session.response}
              text={session.response || 'Ready when you are.'}
              muted={!session.response}
              accent
              streaming={session.state === 'thinking' && !session.response}
            />
          </div>

          {/* Controls */}
          <div className="mt-7 flex flex-wrap items-center justify-center gap-4">
            <div className="flex items-center gap-2.5 rounded-xl border border-border bg-card/40 px-3.5 py-2.5">
              <Switch
                id="always-on"
                checked={session.listeningMode === 'always_on'}
                onCheckedChange={session.toggleMode}
              />
              <Label htmlFor="always-on" className="cursor-pointer text-xs">
                Always listening
                <span className="block text-[0.65rem] font-normal text-muted-foreground">
                  {session.listeningMode === 'always_on'
                    ? 'No wake word needed'
                    : `Waits for "Hey ${wakeName}"`}
                </span>
              </Label>
            </div>

            <Button variant="destructive" className="h-10" onClick={session.stop}>
              <Square className="size-3.5" />
              Stop talking
            </Button>
          </div>

          <p className="mt-4 flex items-center gap-1.5 text-xs text-muted-foreground">
            {session.micStatus === 'active' ? (
              <>
                <Mic className="size-3.5 text-brand" />
                Microphone live — space or escape stops her
              </>
            ) : session.micStatus === 'denied' ? (
              <>
                <MicOff className="size-3.5 text-destructive" />
                Microphone blocked — allow it in your browser settings and reload
              </>
            ) : (
              <>
                <MicOff className="size-3.5" />
                Click anywhere to turn the microphone on
              </>
            )}
          </p>
        </section>

        {/* ── Side rail ──────────────────────────────────────────────────── */}
        <aside className="flex flex-col gap-4">
          {me && (
            <div className="rounded-2xl border border-border bg-card/40 p-5">
              <h2 className="text-xs tracking-widest text-muted-foreground uppercase">
                This month
              </h2>
              <UsageMeter used={me.used} limit={me.limit} className="mt-4" expanded />
              <dl className="mt-5 space-y-2.5 border-t border-border pt-4 text-sm">
                <Row label="Questions asked" value={session.queries} />
                <Row label="Tools used" value={session.tools} />
                <Row label="Plan" value={me.plan} />
                <Row
                  label="Connection"
                  value={session.connected ? 'online' : 'offline'}
                  tone={session.connected ? 'good' : 'bad'}
                />
              </dl>
            </div>
          )}

          <div className="flex min-h-0 flex-1 flex-col rounded-2xl border border-border bg-card/40 p-5">
            <h2 className="text-xs tracking-widest text-muted-foreground uppercase">Activity</h2>
            <div className="mt-4 flex-1 space-y-2 overflow-y-auto pr-1 lg:max-h-[380px]">
              <AnimatePresence initial={false}>
                {session.logs.map((entry) => (
                  <motion.div
                    key={entry.id}
                    layout
                    initial={{ opacity: 0, x: -8 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0 }}
                    transition={{ type: 'spring', stiffness: 400, damping: 36 }}
                    className="flex gap-2.5 font-mono text-[0.7rem] leading-relaxed"
                  >
                    <span className="shrink-0 text-muted-foreground/60">{entry.at}</span>
                    <span
                      className={cn(
                        'min-w-0 break-words',
                        entry.kind === 'error' && 'text-destructive',
                        entry.kind === 'tool' && 'text-brand-soft',
                        entry.kind === 'transcript' && 'text-foreground',
                        entry.kind === 'info' && 'text-muted-foreground',
                      )}
                    >
                      {entry.text}
                    </span>
                  </motion.div>
                ))}
              </AnimatePresence>
              {session.logs.length === 0 && (
                <p className="text-xs text-muted-foreground">Nothing yet.</p>
              )}
            </div>
          </div>
        </aside>
      </main>

      <RenameDialog
        open={renaming}
        current={wakeName}
        onOpenChange={setRenaming}
        onSaved={setWakeName}
      />

      <audio ref={session.playerRef} autoPlay className="hidden" />
    </div>
  )
}

function Row({
  label,
  value,
  tone,
}: {
  label: string
  value: string | number
  tone?: 'good' | 'bad'
}) {
  return (
    <div className="flex items-center justify-between gap-3">
      <dt className="text-muted-foreground">{label}</dt>
      <dd
        className={cn(
          'font-mono text-xs',
          tone === 'good' && 'text-brand',
          tone === 'bad' && 'text-destructive',
          !tone && 'text-foreground',
        )}
      >
        {value}
      </dd>
    </div>
  )
}

function Panel({
  tag,
  text,
  active,
  muted,
  accent,
  streaming,
}: {
  tag: string
  text: string
  active: boolean
  muted?: boolean
  accent?: boolean
  streaming?: boolean
}) {
  return (
    <motion.div
      layout
      className={cn(
        'rounded-xl border px-4 py-3.5 transition-colors',
        active ? 'border-brand/30 bg-brand/[0.04]' : 'border-border bg-card/30',
      )}
    >
      <div className="font-mono text-[0.6rem] tracking-[0.16em] text-muted-foreground uppercase">
        {tag}
      </div>
      <p
        className={cn(
          'mt-1.5 text-sm leading-relaxed',
          accent && !muted && 'text-brand',
          muted && 'text-muted-foreground',
        )}
      >
        {text}
        {streaming && (
          <motion.span
            className="ml-1 inline-block h-3.5 w-0.5 translate-y-0.5 bg-brand"
            animate={{ opacity: [1, 0.15, 1] }}
            transition={{ repeat: Infinity, duration: 0.9 }}
          />
        )}
      </p>
    </motion.div>
  )
}

function RenameDialog({
  open,
  current,
  onOpenChange,
  onSaved,
}: {
  open: boolean
  current: string
  onOpenChange: (v: boolean) => void
  onSaved: (name: string) => void
}) {
  const [value, setValue] = useState(current)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const check = useMemo(() => checkWakeName(value), [value])

  useEffect(() => {
    if (open) {
      setValue(current)
      setError(null)
    }
  }, [open, current])

  async function save() {
    if (!check.ok) {
      setError(check.why)
      return
    }
    setBusy(true)
    try {
      const res = await api.setWakeName(check.name)
      onSaved(res.wake_name)
      onOpenChange(false)
    } catch (ex) {
      setError(ex instanceof Error ? ex.message : 'Could not save the name.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-sm">
        <DialogHeader>
          <DialogTitle>Change the name</DialogTitle>
          <DialogDescription>
            It takes effect on the next thing you say.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3">
          <FormError>{error}</FormError>
          <Input
            value={value}
            maxLength={24}
            autoFocus
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && save()}
            aria-invalid={!check.ok}
          />
          <p className={cn('text-xs', check.ok ? 'text-muted-foreground' : 'text-destructive')}>
            {check.ok ? `You'll say "Hey ${check.name}".` : check.why}
          </p>
        </div>

        <DialogFooter>
          <Button variant="ghost" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={save} disabled={busy || !check.ok}>
            {busy && <Loader2 className="size-3.5 animate-spin" />}
            Save
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
