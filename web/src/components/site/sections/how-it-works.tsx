import { Ear, MessageCircle, Sparkles, Volume2 } from 'lucide-react'
import { Effect } from '@animate-ui/react/primitives/effects/effect'
import { CountingNumber } from '@animate-ui/react/primitives/texts/counting-number'
import { SectionHeading } from '@/components/site/section-heading'

const STEPS = [
  {
    icon: Ear,
    label: 'It waits for its name',
    body: 'The microphone stays open but nothing is sent anywhere until it hears the name you gave it. Phonetic matching means it still wakes when speech recognition spells the name differently.',
  },
  {
    icon: Sparkles,
    label: 'It thinks locally',
    body: 'Your words are transcribed by Whisper and answered by Llama 3.2, both running on the server. Your conversation never reaches a third-party AI service.',
  },
  {
    icon: Volume2,
    label: 'It speaks back',
    body: 'The reply is spoken as it is generated, so you hear the first words while the rest is still being written. Say "stop" and it stops mid-sentence.',
  },
  {
    icon: MessageCircle,
    label: 'It keeps what matters',
    body: 'Worthwhile exchanges and standing preferences are encrypted under a key derived for your account alone, then recalled when they are relevant.',
  },
]

const FACTS = [
  { n: 100, suffix: '', label: 'Free conversations a month' },
  { n: 2, suffix: '', label: 'Languages, English and Telugu' },
  { n: 12, suffix: '', label: 'Things it can do on your machine' },
  { n: 0, suffix: '', label: 'Words sent to an outside AI service' },
]

export function HowItWorks() {
  return (
    <section id="how" className="relative scroll-mt-20 border-y border-border py-24">
      <div className="mx-auto max-w-6xl px-5">
        <SectionHeading
          eyebrow="How it works"
          title="Four steps, start to finish"
          body="From the moment you say its name to the moment it remembers what you said."
        />

        <ol className="mt-14 grid gap-6 md:grid-cols-2 lg:grid-cols-4">
          {STEPS.map((step, i) => (
            <Effect
              key={step.label}
              slide={{ direction: 'up', offset: 18 }}
              fade
              delay={i * 0.08}
              inView
              inViewOnce
              asChild
            >
              <li className="relative">
                <div className="flex items-center gap-3">
                  <span className="flex size-9 shrink-0 items-center justify-center rounded-lg border border-brand/25 bg-brand/10 text-brand">
                    <step.icon className="size-4" />
                  </span>
                  <span className="font-mono text-xs text-muted-foreground">
                    STEP {String(i + 1).padStart(2, '0')}
                  </span>
                </div>
                <h3 className="mt-4 text-base font-medium">{step.label}</h3>
                <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{step.body}</p>
              </li>
            </Effect>
          ))}
        </ol>

        <div className="mt-20 grid gap-px overflow-hidden rounded-2xl border border-border bg-border sm:grid-cols-2 lg:grid-cols-4">
          {FACTS.map((f) => (
            <div key={f.label} className="bg-card/50 px-6 py-7 text-center">
              <div className="font-display text-3xl font-bold text-brand">
                <CountingNumber number={f.n} inView inViewOnce />
                {f.suffix}
              </div>
              <div className="mt-2 text-xs text-muted-foreground">{f.label}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
