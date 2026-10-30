import { useEffect, useMemo, useState } from 'react'
import { Check, Loader2 } from 'lucide-react'
import { motion } from 'motion/react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { FormError } from '@/components/site/form-error'
import { api, checkWakeName } from '@/lib/api'
import { cn } from '@/lib/utils'

const MIN_PASSWORD = 8

type Props = {
  open: boolean
  onOpenChange: (open: boolean) => void
  wakeName: string
  email: string
  onWakeNameSaved: (name: string) => void
}

/** Account settings: what the assistant is called, and the password. */
export function AccountDialog({
  open,
  onOpenChange,
  wakeName,
  email,
  onWakeNameSaved,
}: Props) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Account</DialogTitle>
          <DialogDescription>{email}</DialogDescription>
        </DialogHeader>

        {/* Remounted on open so a half-finished edit is never waiting next time. */}
        {open && (
          <div className="space-y-7">
            <WakeNameSection current={wakeName} onSaved={onWakeNameSaved} />
            <div className="h-px bg-border" />
            <PasswordSection />
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <h3 className="text-xs font-medium tracking-widest text-muted-foreground uppercase">
      {children}
    </h3>
  )
}

/** A confirmation that fades itself out, so there is no stale "Saved" on screen. */
function useFlash() {
  const [message, setMessage] = useState<string | null>(null)
  useEffect(() => {
    if (!message) return
    const id = window.setTimeout(() => setMessage(null), 3000)
    return () => window.clearTimeout(id)
  }, [message])
  return [message, setMessage] as const
}

function Saved({ children }: { children: React.ReactNode }) {
  return (
    <motion.p
      initial={{ opacity: 0, y: -4 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex items-center gap-1.5 text-xs text-brand"
    >
      <Check className="size-3.5" />
      {children}
    </motion.p>
  )
}

function WakeNameSection({
  current,
  onSaved,
}: {
  current: string
  onSaved: (name: string) => void
}) {
  const [value, setValue] = useState(current)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [saved, setSaved] = useFlash()
  const check = useMemo(() => checkWakeName(value), [value])
  const dirty = check.ok && check.name !== current

  async function save() {
    if (!check.ok) return setError(check.why)
    setError(null)
    setBusy(true)
    try {
      const res = await api.setWakeName(check.name)
      onSaved(res.wake_name)
      setSaved(`It answers to ${res.wake_name} now.`)
    } catch (ex) {
      setError(ex instanceof Error ? ex.message : 'Could not save the name.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="space-y-3">
      <SectionTitle>Assistant name</SectionTitle>
      <FormError>{error}</FormError>

      <div className="space-y-2">
        <Label htmlFor="acct-wake">What it answers to</Label>
        <Input
          id="acct-wake"
          value={value}
          maxLength={24}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && dirty && save()}
          aria-invalid={!check.ok}
        />
        <p className={cn('text-xs', check.ok ? 'text-muted-foreground' : 'text-destructive')}>
          {check.ok ? `You'll say "Hey ${check.name}".` : check.why}
        </p>
      </div>

      {saved && <Saved>{saved}</Saved>}

      <Button size="sm" onClick={save} disabled={busy || !dirty}>
        {busy && <Loader2 className="size-3 animate-spin" />}
        Save name
      </Button>
    </section>
  )
}

function PasswordSection() {
  const [current, setCurrent] = useState('')
  const [next, setNext] = useState('')
  const [confirm, setConfirm] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [saved, setSaved] = useFlash()

  const tooShort = next.length > 0 && next.length < MIN_PASSWORD
  const mismatch = confirm.length > 0 && next !== confirm
  const ready = current.length > 0 && next.length >= MIN_PASSWORD && next === confirm

  async function save() {
    setError(null)
    setBusy(true)
    try {
      await api.changePassword(current, next)
      setCurrent('')
      setNext('')
      setConfirm('')
      setSaved('Password changed. Other devices have been signed out.')
    } catch (ex) {
      setError(ex instanceof Error ? ex.message : 'Could not change the password.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="space-y-3">
      <SectionTitle>Password</SectionTitle>
      <FormError>{error}</FormError>

      <div className="space-y-2">
        <Label htmlFor="acct-current">Current password</Label>
        <Input
          id="acct-current"
          type="password"
          autoComplete="current-password"
          value={current}
          onChange={(e) => setCurrent(e.target.value)}
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="acct-new">New password</Label>
        <Input
          id="acct-new"
          type="password"
          autoComplete="new-password"
          value={next}
          onChange={(e) => setNext(e.target.value)}
          aria-invalid={tooShort}
        />
        <p className={cn('text-xs', tooShort ? 'text-destructive' : 'text-muted-foreground')}>
          At least {MIN_PASSWORD} characters.
        </p>
      </div>

      <div className="space-y-2">
        <Label htmlFor="acct-confirm">Repeat the new password</Label>
        <Input
          id="acct-confirm"
          type="password"
          autoComplete="new-password"
          value={confirm}
          onChange={(e) => setConfirm(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && ready && save()}
          aria-invalid={mismatch}
        />
        {mismatch && <p className="text-xs text-destructive">The two do not match.</p>}
      </div>

      {saved && <Saved>{saved}</Saved>}

      <Button size="sm" onClick={save} disabled={busy || !ready}>
        {busy && <Loader2 className="size-3 animate-spin" />}
        Change password
      </Button>
    </section>
  )
}
