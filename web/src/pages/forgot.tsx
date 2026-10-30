import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Loader2, MailCheck } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { AuthShell } from '@/components/site/auth-shell'
import { FormError } from '@/components/site/form-error'
import { api } from '@/lib/api'

export default function ForgotPage() {
  const [email, setEmail] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [sent, setSent] = useState(false)
  const [busy, setBusy] = useState(false)

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setBusy(true)
    try {
      await api.forgotPassword(email)
      setSent(true)
    } catch (ex) {
      setError(ex instanceof Error ? ex.message : 'Could not send the code.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <AuthShell
      title="Forgotten password"
      lead="Tell us the address on the account and we will send a code to reset it."
      aside={{
        heading: 'Only the inbox can let you back in',
        points: [
          'The code goes to the address on the account and nowhere else.',
          'It expires in ten minutes and can only be used once.',
          'Resetting signs every other device out of the account.',
        ],
      }}
    >
      {sent ? (
        <div className="space-y-5">
          <p className="flex items-start gap-2.5 rounded-lg border border-brand/25 bg-brand/8 px-3 py-3 text-sm text-brand">
            <MailCheck className="mt-0.5 size-4 shrink-0" />
            If that address has an account, a code is on its way. It expires in ten minutes.
          </p>
          <Button className="h-10 w-full" asChild>
            <Link to={`/reset?email=${encodeURIComponent(email)}`}>I have the code</Link>
          </Button>
          <p className="text-center text-sm text-muted-foreground">
            <button onClick={() => setSent(false)} className="text-brand hover:underline">
              Use a different address
            </button>
          </p>
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
              autoFocus
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
            />
          </div>

          <Button type="submit" className="h-10 w-full" disabled={busy || !email}>
            {busy && <Loader2 className="size-4 animate-spin" />}
            {busy ? 'Sending' : 'Send me a code'}
          </Button>

          <p className="text-center text-sm text-muted-foreground">
            Remembered it?{' '}
            <Link to="/login" className="text-brand hover:underline">
              Sign in
            </Link>
          </p>
        </form>
      )}
    </AuthShell>
  )
}
