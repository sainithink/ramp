import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { AnimatePresence, motion } from 'motion/react'
import {
  CheckCircle2,
  Loader2,
  LogOut,
  MessageSquare,
  Shield,
  SlidersHorizontal,
  Users,
} from 'lucide-react'
import { Effect } from '@animate-ui/react/primitives/effects/effect'
import { CountingNumber } from '@animate-ui/react/primitives/texts/counting-number'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { UsageMeter } from '@/components/usage-meter'
import { Wordmark } from '@/components/site/wordmark'
import { FormError } from '@/components/site/form-error'
import { ApiError, api, checkWakeName, type AdminPayload, type AdminUser } from '@/lib/api'
import { cn } from '@/lib/utils'

export default function AdminPage() {
  const [data, setData] = useState<AdminPayload | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [editing, setEditing] = useState<AdminUser | null>(null)

  const load = useCallback(async () => {
    try {
      setData(await api.adminUsers())
    } catch (ex) {
      if (ex instanceof ApiError && ex.status === 403) {
        window.location.href = '/app'
        return
      }
      if (ex instanceof ApiError && ex.status === 401) {
        window.location.href = '/login'
        return
      }
      setError(ex instanceof Error ? ex.message : 'Could not load users.')
    }
  }, [])

  useEffect(() => {
    void load()
    // Usage counters move while people are talking.
    const id = window.setInterval(() => void load(), 30000)
    return () => window.clearInterval(id)
  }, [load])

  const flash = useCallback((msg: string) => {
    setNotice(msg)
    window.setTimeout(() => setNotice(null), 3500)
  }, [])

  const update = useCallback(
    async (id: string, body: Record<string, unknown>, okMsg: string) => {
      setError(null)
      try {
        await api.adminUpdate(id, body)
        flash(okMsg)
      } catch (ex) {
        setError(ex instanceof Error ? ex.message : 'Update failed.')
      } finally {
        void load()
      }
    },
    [flash, load],
  )

  const stats = useMemo(
    () =>
      data
        ? [
            { icon: Users, label: 'Total users', value: data.stats.total_users },
            { icon: CheckCircle2, label: 'Active', value: data.stats.active_users },
            { icon: Shield, label: 'Admins', value: data.stats.admins },
            {
              icon: MessageSquare,
              label: 'Conversations this month',
              value: data.stats.conversations_this_month,
            },
          ]
        : [],
    [data],
  )

  if (!data) {
    return (
      <div className="grid min-h-dvh place-items-center">
        {error ? (
          <div className="max-w-sm px-5">
            <FormError>{error}</FormError>
          </div>
        ) : (
          <Loader2 className="size-5 animate-spin text-brand" />
        )}
      </div>
    )
  }

  return (
    <div className="min-h-dvh">
      <header className="glass sticky top-0 z-40 border-b border-border">
        <div className="mx-auto flex h-14 max-w-7xl items-center gap-3 px-5">
          <Wordmark to="/app" />
          <Badge variant="outline" className="border-amber-400/40 text-amber-400">
            Admin
          </Badge>
          <div className="ml-auto flex items-center gap-2">
            <Button variant="ghost" size="sm" asChild>
              <Link to="/app">Assistant</Link>
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={async () => {
                await api.logout().catch(() => {})
                window.location.href = '/'
              }}
            >
              <LogOut className="size-3.5" />
              Sign out
            </Button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-5 py-8">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="text-xl font-semibold tracking-tight">Users and usage</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              Set plans and limits. Conversation contents are encrypted per account and
              are not readable here.
            </p>
          </div>
        </div>

        <div className="mt-6 space-y-3">
          <FormError>{error}</FormError>
          <AnimatePresence>
            {notice && (
              <motion.div
                initial={{ opacity: 0, y: -6 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                className="flex items-center gap-2 rounded-lg border border-brand/30 bg-brand/8 px-3 py-2.5 text-sm text-brand"
              >
                <CheckCircle2 className="size-4" />
                {notice}
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {stats.map((s, i) => (
            <Effect key={s.label} slide={{ direction: 'up', offset: 12 }} fade delay={i * 0.06}>
              <div className="rounded-2xl border border-border bg-card/40 p-5">
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <s.icon className="size-3.5" />
                  {s.label}
                </div>
                <div className="mt-2 font-display text-3xl font-bold text-brand">
                  <CountingNumber number={s.value} />
                </div>
              </div>
            </Effect>
          ))}
        </div>

        <div className="mt-8 overflow-hidden rounded-2xl border border-border">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="border-b border-border bg-card/60">
                <tr className="text-left text-xs tracking-wider text-muted-foreground uppercase">
                  <th className="px-5 py-3 font-medium">User</th>
                  <th className="px-5 py-3 font-medium">Answers to</th>
                  <th className="px-5 py-3 font-medium">Plan</th>
                  <th className="px-5 py-3 font-medium">This month</th>
                  <th className="px-5 py-3 font-medium">All time</th>
                  <th className="px-5 py-3 font-medium">Status</th>
                  <th className="px-5 py-3 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {data.users.map((u) => (
                  <tr key={u.id} className="border-b border-border/60 last:border-0 hover:bg-card/40">
                    <td className="px-5 py-4">
                      <div className="font-medium">{u.display_name || '—'}</div>
                      <div className="text-xs text-muted-foreground">{u.email}</div>
                    </td>
                    <td className="px-5 py-4 font-mono text-xs text-brand">{u.wake_name}</td>
                    <td className="px-5 py-4">
                      <div className="flex flex-wrap items-center gap-1.5">
                        <Badge variant="outline">{u.plan}</Badge>
                        {u.role === 'admin' && (
                          <Badge variant="outline" className="border-amber-400/40 text-amber-400">
                            admin
                          </Badge>
                        )}
                      </div>
                      {u.custom_limit !== null && (
                        <div className="mt-1 text-[0.65rem] text-muted-foreground">
                          custom limit {u.custom_limit}
                        </div>
                      )}
                    </td>
                    <td className="px-5 py-4">
                      <UsageMeter used={u.used} limit={u.limit} className="flex" />
                    </td>
                    <td className="px-5 py-4 font-mono text-xs text-muted-foreground">{u.total}</td>
                    <td className="px-5 py-4">
                      <Badge
                        variant="outline"
                        className={cn(
                          u.is_active
                            ? 'border-brand/35 text-brand'
                            : 'border-destructive/40 text-destructive',
                        )}
                      >
                        {u.is_active ? 'active' : 'disabled'}
                      </Badge>
                    </td>
                    <td className="px-5 py-4">
                      <div className="flex flex-wrap items-center gap-2">
                        <Select
                          value={u.plan}
                          onValueChange={(plan) =>
                            void update(u.id, { plan }, `${u.email} moved to ${plan}.`)
                          }
                        >
                          <SelectTrigger size="sm" className="w-[108px]">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            {Object.entries(data.plans).map(([plan, limit]) => (
                              <SelectItem key={plan} value={plan}>
                                {plan} ({limit})
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>

                        <Button variant="outline" size="sm" onClick={() => setEditing(u)}>
                          <SlidersHorizontal className="size-3" />
                          Edit
                        </Button>

                        <Button
                          variant={u.is_active ? 'destructive' : 'outline'}
                          size="sm"
                          onClick={() =>
                            void update(
                              u.id,
                              { is_active: !u.is_active },
                              u.is_active ? 'Account disabled.' : 'Account enabled.',
                            )
                          }
                        >
                          {u.is_active ? 'Disable' : 'Enable'}
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {data.users.length === 0 && (
            <p className="p-10 text-center text-sm text-muted-foreground">No users yet.</p>
          )}
        </div>
      </main>

      <EditUserDialog
        user={editing}
        plans={data.plans}
        onClose={() => setEditing(null)}
        onSave={update}
      />
    </div>
  )
}

function EditUserDialog({
  user,
  plans,
  onClose,
  onSave,
}: {
  user: AdminUser | null
  plans: Record<string, number>
  onClose: () => void
  onSave: (id: string, body: Record<string, unknown>, okMsg: string) => Promise<void>
}) {
  const [wake, setWake] = useState('')
  const [limit, setLimit] = useState('')
  const [role, setRole] = useState('user')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (user) {
      setWake(user.wake_name)
      setLimit(user.custom_limit === null ? '' : String(user.custom_limit))
      setRole(user.role)
      setError(null)
    }
  }, [user])

  const nameCheck = useMemo(() => checkWakeName(wake), [wake])

  async function submit() {
    if (!user) return
    if (!nameCheck.ok) {
      setError(nameCheck.why)
      return
    }
    const body: Record<string, unknown> = {}
    if (nameCheck.name !== user.wake_name) body.wake_name = nameCheck.name
    if (role !== user.role) body.role = role

    const trimmed = limit.trim()
    if (trimmed === '' && user.custom_limit !== null) {
      body.clear_custom_limit = true
    } else if (trimmed !== '') {
      const n = Number.parseInt(trimmed, 10)
      if (Number.isNaN(n) || n < 0) {
        setError('Enter a whole number of conversations, or leave it blank for the plan default.')
        return
      }
      if (n !== user.custom_limit) body.custom_limit = n
    }

    if (Object.keys(body).length === 0) {
      onClose()
      return
    }

    setBusy(true)
    await onSave(user.id, body, `${user.email} updated.`)
    setBusy(false)
    onClose()
  }

  return (
    <Dialog open={!!user} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Edit {user?.email}</DialogTitle>
          <DialogDescription>
            Leave the limit blank to fall back to the plan default
            {user ? ` (${plans[user.plan] ?? '—'})` : ''}.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <FormError>{error}</FormError>

          <div className="space-y-2">
            <Label htmlFor="a-wake">Answers to</Label>
            <Input
              id="a-wake"
              value={wake}
              maxLength={24}
              onChange={(e) => setWake(e.target.value)}
              aria-invalid={!nameCheck.ok}
            />
            {!nameCheck.ok && <p className="text-xs text-destructive">{nameCheck.why}</p>}
          </div>

          <div className="space-y-2">
            <Label htmlFor="a-limit">Monthly conversation limit</Label>
            <Input
              id="a-limit"
              inputMode="numeric"
              value={limit}
              placeholder="Plan default"
              onChange={(e) => setLimit(e.target.value)}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="a-role">Role</Label>
            <Select value={role} onValueChange={setRole}>
              <SelectTrigger id="a-role" className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="user">user</SelectItem>
                <SelectItem value="admin">admin</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        <DialogFooter>
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={submit} disabled={busy}>
            {busy && <Loader2 className="size-3.5 animate-spin" />}
            Save changes
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
