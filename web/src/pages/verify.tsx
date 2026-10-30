import { useEffect, useState } from 'react'
import { Loader2, MailCheck } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { AuthShell } from '@/components/site/auth-shell'
import { FormError } from '@/components/site/form-error'
import { CodeField } from '@/components/site/code-field'
import { useCountdown } from '@/hooks/use-countdown'
import { ApiError, api } from '@/lib/api'

const RESEND_SECONDS = 60

export default function VerifyPage() {
  const [email, setEmail] = useState('')
  const [code, setCode] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [loading, setLoading] = useState(true)
  const { left, start } = useCountdown(RESEND_SECONDS)

  useEffect(() => {
    api
      .me()
      .then((me) => {
        if (me.verified) {
          window.location.href = '/app'
          return
        }
        setEmail(me.email)
        setLoading(false)
      })
      .catch((ex) => {
        if (ex instanceof ApiError && ex.status === 401) window.location.href = '/login'
      })
  }, [])

  async function submit(value = code) {
    if (value.length < 6) return
    setError(null)
    setBusy(true)
    try {
      await api.confirmVerifyCode(value)
      window.location.href = '/app'
    } catch (ex) {
      setError(ex instanceof Error ? ex.message : 'Could not check that code.')
      setCode('')
      setBusy(false)
    }
  }

  async function resend() {
    setError(null)
    setNotice(null)
    try {
      const res = await api.sendVerifyCode()
      setNotice(
        res.code_sent
          ? 'A new code is on its way.'
          : 'Email is not configured on this server — the code is in the server log.',
      )
      start(RESEND_SECONDS)
    } catch (ex) {
      setError(ex instanceof Error ? ex.message : 'Could not send a new code.')
    }
  }

  if (loading) {
    return (
      <div className="grid min-h-dvh place-items-center">
        <Loader2 className="size-5 animate-spin text-brand" />
      </div>
    )
  }

  return (
    <AuthShell
      title="Check your email"
      lead={`We sent a six-digit code to ${email}. It expires in ten minutes.`}
      aside={{
        heading: 'One step and you are in',
        points: [
          'The code proves the address is yours, so a password reset can reach you later.',
          'It can only be used once, and it stops working after five wrong guesses.',
          'Nothing was sent anywhere else — the address is only ever used for your own account.',
        ],
      }}
    >
      <div className="space-y-5">
        <FormError>{error}</FormError>
        {notice && (
          <p className="flex items-center gap-2 rounded-lg border border-brand/25 bg-brand/8 px-3 py-2.5 text-sm text-brand">
            <MailCheck className="size-4 shrink-0" />
            {notice}
          </p>
        )}

        <CodeField value={code} onChange={setCode} onComplete={submit} disabled={busy} />

        <Button className="h-10 w-full" onClick={() => submit()} disabled={busy || code.length < 6}>
          {busy && <Loader2 className="size-4 animate-spin" />}
          {busy ? 'Checking' : 'Activate my account'}
        </Button>

        <div className="text-center text-sm text-muted-foreground">
          {left > 0 ? (
            <span>You can ask for another code in {left}s</span>
          ) : (
            <button onClick={resend} className="text-brand hover:underline">
              Send me another code
            </button>
          )}
        </div>

        <div className="text-center">
          <button
            onClick={async () => {
              await api.logout().catch(() => {})
              window.location.href = '/'
            }}
            className="text-xs text-muted-foreground hover:text-foreground"
          >
            Sign out
          </button>
        </div>
      </div>
    </AuthShell>
  )
}
