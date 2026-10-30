import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { Check, Loader2, X } from 'lucide-react'
import { motion } from 'motion/react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { AuthShell } from '@/components/site/auth-shell'
import { FormError } from '@/components/site/form-error'
import { api, checkWakeName } from '@/lib/api'

const SUGGESTIONS = ['Saira', 'Jarvis', 'Nova', 'Krishna', 'Ammu']

export default function RegisterPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [wake, setWake] = useState('Saira')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const nameCheck = useMemo(() => checkWakeName(wake), [wake])

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    if (!nameCheck.ok) {
      setError(nameCheck.why)
      return
    }
    setBusy(true)
    try {
      await api.register(email, password, nameCheck.name, displayName)
      window.location.href = '/app'
    } catch (ex) {
      setError(ex instanceof Error ? ex.message : 'Could not create the account.')
      setBusy(false)
    }
  }

  return (
    <AuthShell
      title="Create your assistant"
      lead="Free — 100 conversations a month, no card needed."
      aside={{
        heading: 'You decide what it answers to',
        points: [
          'Pick the name now; it is matched phonetically so it wakes even on a near miss.',
          'Everything you tell it is encrypted under a key derived for your account alone.',
          'All nine things it can do are in the free tier, including Telugu.',
        ],
      }}
    >
      <form onSubmit={onSubmit} noValidate className="space-y-5">
        <FormError>{error}</FormError>

        <div className="space-y-2">
          <Label htmlFor="email">Email</Label>
          <Input
            id="email"
            type="email"
            autoComplete="email"
            autoFocus
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="display">
            Your name <span className="text-muted-foreground">(optional)</span>
          </Label>
          <Input
            id="display"
            autoComplete="name"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            placeholder="What it should call you"
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="password">Password</Label>
          <Input
            id="password"
            type="password"
            autoComplete="new-password"
            required
            minLength={8}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="At least 8 characters"
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="wake">What should it answer to?</Label>
          <Input
            id="wake"
            value={wake}
            maxLength={24}
            onChange={(e) => setWake(e.target.value)}
            aria-invalid={!nameCheck.ok}
          />

          <motion.div
            layout
            className={[
              'flex items-start gap-2 rounded-lg border px-3 py-2.5 text-sm',
              nameCheck.ok
                ? 'border-brand/25 bg-brand/8 text-brand'
                : 'border-destructive/40 bg-destructive/10 text-destructive',
            ].join(' ')}
          >
            {nameCheck.ok ? (
              <Check className="mt-0.5 size-4 shrink-0" />
            ) : (
              <X className="mt-0.5 size-4 shrink-0" />
            )}
            <span>
              {nameCheck.ok ? (
                <>
                  You&rsquo;ll say{' '}
                  <strong className="font-medium">&ldquo;Hey {nameCheck.name}&rdquo;</strong> to wake it.
                </>
              ) : (
                nameCheck.why
              )}
            </span>
          </motion.div>

          <div className="flex flex-wrap gap-1.5 pt-1">
            {SUGGESTIONS.map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => setWake(s)}
                className="rounded-full border border-border px-2.5 py-1 text-xs text-muted-foreground transition-colors hover:border-brand/40 hover:text-brand"
              >
                {s}
              </button>
            ))}
          </div>

          <p className="text-xs text-muted-foreground">
            One word, letters only, 3&ndash;24 characters. You can change it later.
          </p>
        </div>

        <Button type="submit" className="h-10 w-full" disabled={busy}>
          {busy && <Loader2 className="size-4 animate-spin" />}
          {busy ? 'Creating' : 'Create account'}
        </Button>

        <p className="text-center text-sm text-muted-foreground">
          Already have an account?{' '}
          <Link to="/login" className="text-brand hover:underline">
            Sign in
          </Link>
        </p>
      </form>
    </AuthShell>
  )
}
