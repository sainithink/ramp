import { CountingNumber } from '@animate-ui/react/primitives/texts/counting-number'
import { motion } from 'motion/react'
import { cn } from '@/lib/utils'

type Props = {
  used: number
  limit: number
  /** Adds the written-out "x of y conversations" line beneath the bar. */
  expanded?: boolean
  className?: string
}

/** Amber past 80% of the limit, red once it is reached. */
export function UsageMeter({ used, limit, expanded, className }: Props) {
  const ratio = limit > 0 ? Math.min(1, used / limit) : 0
  const tone = ratio >= 1 ? 'bad' : ratio >= 0.8 ? 'warn' : 'ok'

  const bar =
    tone === 'bad'
      ? 'bg-destructive'
      : tone === 'warn'
        ? 'bg-amber-400'
        : 'bg-brand'

  if (!expanded) {
    return (
      <div className={cn('items-center gap-2', className)} title={`${used} of ${limit} this month`}>
        <div className="h-1 w-16 overflow-hidden rounded-full bg-muted">
          <motion.div
            className={cn('h-full rounded-full', bar)}
            initial={false}
            animate={{ width: `${ratio * 100}%` }}
            transition={{ type: 'spring', stiffness: 160, damping: 24 }}
          />
        </div>
        <span
          className={cn(
            'font-mono text-xs',
            tone === 'bad' && 'text-destructive',
            tone === 'warn' && 'text-amber-400',
            tone === 'ok' && 'text-muted-foreground',
          )}
        >
          {used}/{limit}
        </span>
      </div>
    )
  }

  return (
    <div className={className}>
      <div className="flex items-baseline justify-between">
        <span className="font-display text-2xl font-bold">
          <CountingNumber number={used} />
        </span>
        <span className="font-mono text-xs text-muted-foreground">of {limit}</span>
      </div>
      <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-muted">
        <motion.div
          className={cn('h-full rounded-full', bar)}
          initial={false}
          animate={{ width: `${ratio * 100}%` }}
          transition={{ type: 'spring', stiffness: 160, damping: 24 }}
        />
      </div>
      <p className="mt-2 text-xs text-muted-foreground">
        {ratio >= 1
          ? 'Monthly limit reached — it resets on the first.'
          : `${limit - used} conversations left this month.`}
      </p>
    </div>
  )
}
