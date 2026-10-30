import { Fingerprint, KeyRound, Lock, Server, SquareSlash, Waves } from 'lucide-react'
import { Effect } from '@animate-ui/react/primitives/effects/effect'
import { SectionHeading } from '@/components/site/section-heading'

const FEATURES = [
  {
    icon: Fingerprint,
    title: 'Name it whatever you like',
    body: 'Jarvis, Nova, Krishna, Ammu — you pick the name when you sign up and can change it later. It is matched phonetically, so it answers even when a transcript spells it wrong.',
  },
  {
    icon: Lock,
    title: 'Encrypted per account',
    body: 'Each account gets its own key, derived separately for memories, preferences and profile. One account cannot decrypt another’s data, even on the same server.',
  },
  {
    icon: Server,
    title: 'Nothing leaves the box',
    body: 'Speech recognition, the language model and the voice all run on the same server. There is no API key to a third-party AI service because there is no third-party AI service.',
  },
  {
    icon: SquareSlash,
    title: 'Interrupt it any time',
    body: 'Say "stop", hit space, or press escape and it stops talking immediately — mid-word if that is where you caught it.',
  },
  {
    icon: Waves,
    title: 'Answers while it writes',
    body: 'The voice starts on the first sentence rather than the last, so there is no silent wait while a long answer is composed.',
  },
  {
    icon: KeyRound,
    title: 'Your own account',
    body: 'Sign in from anywhere, with your own name, your own memory and your own usage. Admins can see totals and set limits, never your conversations.',
  },
]

export function Features() {
  return (
    <section id="features" className="relative scroll-mt-20 py-24">
      <div className="mx-auto max-w-6xl px-5">
        <SectionHeading
          eyebrow="Features"
          title="Built to be yours, not everybody’s"
          body="The things that are hard to get right in a voice assistant, done properly."
        />

        <div className="mt-14 grid gap-10 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map((f, i) => (
            <Effect
              key={f.title}
              slide={{ direction: 'up', offset: 16 }}
              fade
              delay={(i % 3) * 0.07}
              inView
              inViewOnce
            >
              <div>
                <f.icon className="size-5 text-brand" />
                <h3 className="mt-4 text-base font-medium">{f.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{f.body}</p>
              </div>
            </Effect>
          ))}
        </div>
      </div>
    </section>
  )
}
