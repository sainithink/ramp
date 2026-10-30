import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { CheckCircle2, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { AuthShell } from '@/components/site/auth-shell'
import { FormError } from '@/components/site/form-error'
import { CodeField } from '@/components/site/code-field'
import { api } from '@/lib/api'
import { cn } from '@/lib/utils'

const MIN_PASSWORD = 8

export default function ResetPage() {
  const [params] = useSearchParams()
  const [email, setEmail] = useState(params.get('email') ?? '')
  const [code, setCode] = useState('')
  const [next, setNext] = useState('')
  const [confirm, setConfirm] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [done, setDone] = useState(false)
  const [busy, setBusy] = useState(false)

  const tooShort = next.length > 0 && next.length < MIN_PASSWORD
  const mismatch = confirm.length > 0 && next !== confirm
  const ready =
    email.length > 0 && code.length === 6 && next.length >= MIN_PASSWORD && next === confirm

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setBusy(true)
    try {
      await api.resetPassword(email, code, next)
      setDone(true)
    } catch (ex) {
      setError(ex instanceof Error ? ex.message : 'Could not reset the password.')
      setCode('')
    } finally {
      setBusy(false)
    }
  }

  return (
    <AuthShell
      title={done ? 'Password changed' : 'Choose a new password'}
      lead={
        done
          ? 'You can sign in with it now.'
          : 'Enter the code from the email and the password you want instead.'
      }
      aside={{
        heading: 'Everything else gets signed out',
        points: [
          'Any device still signed in to this account is signed out when the password changes.',
          'The code works once, then it is spent.',
          'Using the code also confirms the address, if it was never confirmed.',
        ],
      }}
    >
      {done ? (
        <div className="space-y-5">
          <p className="flex items-start gap-2.5 rounded-lg border border-brand/25 bg-brand/8 px-3 py-3 text-sm text-brand">
            <CheckCircle2 className="mt-0.5 size-4 shrink-0" />
            Your password has been changed and other devices have been signed out.
          </p>
          <Button className="h-10 w-full" asChild>
            <Link to="/login">Sign in</Link>
          </Button>
        </div>
      ) : (
        <form onSubmit={onSubmit} noValidate className="space-y-5">
          <FormError>{error}</FormError>

          <div className="space-y-2">
            <Label htmlFor="email">Email</Label>
            <Input
              id="email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
            />
          </div>

          <div className="space-y-2">
            <Label>Code from the email</Label>
            <CodeField value={code} onChange={setCode} disabled={busy} />
          </div>

          <div className="space-y-2">
            <Label htmlFor="new">New password</Label>
            <Input
              id="new"
              type="password"
              autoComplete="new-password"
              required
              value={next}
              onChange={(e) => setNext(e.target.value)}
              aria-invalid={tooShort}
            />
            <p className={cn('text-xs', tooShort ? 'text-destructive' : 'text-muted-foreground')}>
              At least {MIN_PASSWORD} characters.
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="confirm">Repeat it</Label>
            <Input
              id="confirm"
              type="password"
              autoComplete="new-password"
              required
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              aria-invalid={mismatch}
            />
            {mismatch && <p className="text-xs text-destructive">The two do not match.</p>}
          </div>

          <Button type="submit" className="h-10 w-full" disabled={busy || !ready}>
            {busy && <Loader2 className="size-4 animate-spin" />}
            {busy ? 'Saving' : 'Set the new password'}
          </Button>

          <p className="text-center text-sm text-muted-foreground">
            Need a new code?{' '}
            <Link to="/forgot" className="text-brand hover:underline">
              Ask for one
            </Link>
          </p>
        </form>
      )}
    </AuthShell>
  )
}
