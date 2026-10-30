import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { AuthShell } from '@/components/site/auth-shell'
import { FormError } from '@/components/site/form-error'
import { api } from '@/lib/api'

export default function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setBusy(true)
    try {
      await api.login(email, password)
      // A full load lets the server set up the session page as it sees fit.
      window.location.href = '/app'
    } catch (ex) {
      setError(ex instanceof Error ? ex.message : 'Could not sign in.')
      setBusy(false)
    }
  }

  return (
    <AuthShell
      title="Welcome back"
      lead="Sign in and pick up where you left off."
      aside={{
        heading: 'It still remembers what you told it',
        points: [
          'Your conversations and preferences are waiting, encrypted under your own key.',
          'The name you chose is still the name it answers to.',
          'Your monthly usage resets on the first.',
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
          <Label htmlFor="password">Password</Label>
          <Input
            id="password"
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </div>

        <Button type="submit" className="h-10 w-full" disabled={busy}>
          {busy && <Loader2 className="size-4 animate-spin" />}
          {busy ? 'Signing in' : 'Sign in'}
        </Button>

        <p className="text-center text-sm text-muted-foreground">
          No account yet?{' '}
          <Link to="/register" className="text-brand hover:underline">
            Create one
          </Link>
        </p>
      </form>
    </AuthShell>
  )
}
