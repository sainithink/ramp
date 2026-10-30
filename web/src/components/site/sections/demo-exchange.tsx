import { useEffect, useState } from 'react'
import { AnimatePresence, motion } from 'motion/react'
import { TypingText } from '@animate-ui/react/primitives/texts/typing'
import { cn } from '@/lib/utils'

/**
 * A looping sample conversation. Every line here is something the assistant
 * actually does — the tools behind them are in tools/.
 */
const SCRIPT = [
  {
    ask: 'Hey Saira, play Arijit Singh on YouTube',
    reply: 'Playing Arijit Singh. Opening it now.',
    tool: 'play_youtube',
  },
  {
    ask: 'What’s the weather in Hyderabad?',
    reply: '28°C and clear. It drops to 19°C tonight.',
    tool: 'get_weather',
  },
  {
    ask: 'Call me Sai from now on',
    reply: 'Got it, Sai. I’ll remember that.',
    tool: 'preference saved',
  },
  {
    ask: 'What’s my favourite colour?',
    reply: 'Green, Sai — you told me a while back.',
    tool: 'memory recall',
  },
]

const TYPE_MS = 1400
const REPLY_DELAY = TYPE_MS + 450
const HOLD = 2600

export function DemoExchange({ className }: { className?: string }) {
  const [step, setStep] = useState(0)
  const [phase, setPhase] = useState<'asking' | 'replying'>('asking')

  useEffect(() => {
    setPhase('asking')
    const toReply = window.setTimeout(() => setPhase('replying'), REPLY_DELAY)
    const toNext = window.setTimeout(
      () => setStep((s) => (s + 1) % SCRIPT.length),
      REPLY_DELAY + TYPE_MS + HOLD,
    )
    return () => {
      window.clearTimeout(toReply)
      window.clearTimeout(toNext)
    }
  }, [step])

  const current = SCRIPT[step]

  return (
    <div
      className={cn(
        'glass rounded-2xl border border-border p-4 shadow-2xl shadow-black/40',
        className,
      )}
    >
      <div className="flex items-center gap-2 border-b border-border pb-3">
        <span className="size-1.5 rounded-full bg-brand shadow-[0_0_8px_var(--brand)]" />
        <span className="font-mono text-[0.65rem] tracking-widest text-muted-foreground uppercase">
          Live session
        </span>
        <span className="ml-auto font-mono text-[0.65rem] text-brand/70">
          {phase === 'asking' ? 'listening' : 'speaking'}
        </span>
      </div>

      <div className="mt-3 min-h-[5.5rem] space-y-3">
        <p className="font-mono text-sm text-foreground">
          <TypingText key={`ask-${step}`} text={current.ask} duration={28} />
        </p>

        <AnimatePresence mode="wait">
          {phase === 'replying' && (
            <motion.div
              key={`reply-${step}`}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              transition={{ type: 'spring', stiffness: 300, damping: 30 }}
            >
              <p className="font-mono text-sm text-brand">
                <TypingText text={current.reply} duration={24} />
              </p>
              <span className="mt-2 inline-block rounded border border-border px-1.5 py-0.5 font-mono text-[0.6rem] text-muted-foreground">
                {current.tool}
              </span>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}
