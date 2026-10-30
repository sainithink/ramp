import type { ReactNode } from 'react'
import { Effect } from '@animate-ui/react/primitives/effects/effect'
import { StarsBackground } from '@/components/animate-ui/backgrounds/stars'
import { Robot } from '@/components/robot'
import { Wordmark } from './wordmark'

type Props = {
  title: string
  lead: string
  children: ReactNode
  aside: { heading: string; points: string[] }
}

/** Two-up auth layout: the form on the left, the pitch on the right. */
export function AuthShell({ title, lead, children, aside }: Props) {
  return (
    <div className="grid min-h-dvh lg:grid-cols-2">
      <div className="flex flex-col px-6 py-8 sm:px-12">
        <Wordmark />

        <div className="flex flex-1 items-center">
          <Effect slide={{ direction: 'up', offset: 16 }} fade blur className="w-full">
            <div className="mx-auto w-full max-w-sm py-10">
              <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
              <p className="mt-2 text-sm text-muted-foreground">{lead}</p>
              <div className="mt-8">{children}</div>
            </div>
          </Effect>
        </div>
      </div>

      <div className="relative hidden overflow-hidden border-l border-border lg:block">
        <StarsBackground className="absolute inset-0" starColor="#8affc4" factor={0.02} />
        <div
          aria-hidden
          className="absolute inset-0"
          style={{
            background:
              'radial-gradient(60% 50% at 50% 30%, color-mix(in oklab, var(--brand) 14%, transparent), transparent 70%)',
          }}
        />
        <div className="relative flex h-full flex-col items-center justify-center px-14 text-center">
          <Robot mood="idle" className="w-40" />
          <h2 className="mt-10 text-xl font-medium text-balance">{aside.heading}</h2>
          <ul className="mt-6 space-y-3 text-sm text-muted-foreground">
            {aside.points.map((p) => (
              <li key={p} className="flex items-start gap-2.5 text-left">
                <span className="mt-1.5 size-1.5 shrink-0 rounded-full bg-brand" />
                {p}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  )
}
