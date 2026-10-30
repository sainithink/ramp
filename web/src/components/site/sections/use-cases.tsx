import {
  AppWindow,
  BookOpen,
  BrainCircuit,
  CloudSun,
  Languages,
  Laptop,
  MessageSquareQuote,
  Music,
  Search,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { Effect } from '@animate-ui/react/primitives/effects/effect'
import { Tilt, TiltContent } from '@animate-ui/react/primitives/effects/tilt'
import { SectionHeading } from '@/components/site/section-heading'

type UseCase = {
  icon: LucideIcon
  title: string
  body: string
  says: string[]
  /** Needs SAIRA running on the machine it is driving, not on a server. */
  desktopOnly?: boolean
}

/**
 * Each card maps to something that is really wired up — the tools live in
 * tools/ (play_youtube, open_website, get_weather, …) and memory lives in
 * core/userdata.py. Nothing here is aspirational.
 */
const USE_CASES: UseCase[] = [
  {
    icon: Music,
    title: 'Put music and video on',
    desktopOnly: true,
    body: 'Name a song, an artist or a video and it finds it on YouTube and starts playing — no typing, no tab hunting.',
    says: ['Play Arijit Singh', 'Put on some lo-fi', 'Play the new Pushpa song'],
  },
  {
    icon: AppWindow,
    title: 'Open sites and apps',
    desktopOnly: true,
    body: 'It opens any website or app on the machine by name, so you can keep your hands where they are.',
    says: ['Open sainith.in', 'Open Spotify', 'Open my GitHub'],
  },
  {
    icon: Laptop,
    title: 'Run your computer',
    desktopOnly: true,
    body: 'Volume, mute, screenshots, and what is playing right now — the small things you reach for a dozen times a day.',
    says: ['Turn the volume down to 20', 'Mute it', 'Take a screenshot', 'What’s playing?'],
  },
  {
    icon: Search,
    title: 'Search without stopping',
    desktopOnly: true,
    body: 'Ask it to look something up and it runs the search and opens the results while you carry on talking.',
    says: ['Google the PERM processing times', 'Look up train times to Warangal'],
  },
  {
    icon: BrainCircuit,
    title: 'Ask it anything',
    body: 'General questions answered by a language model running locally. Nothing you ask leaves the server.',
    says: ['Explain what a PERM audit is', 'Say that again more simply', 'Help me word this email'],
  },
  {
    icon: MessageSquareQuote,
    title: 'Tell it once, it sticks',
    body: 'Standing preferences and past conversations are kept, encrypted, and brought back when they matter.',
    says: ['Call me Sai from now on', 'What’s my favourite colour?', 'Remember my sister’s birthday'],
  },
  {
    icon: CloudSun,
    title: 'Check the weather',
    body: 'Live conditions and the forecast for any city, read out in a sentence instead of a table.',
    says: ['What’s the weather in Hyderabad?', 'Will it rain tomorrow?'],
  },
  {
    icon: Languages,
    title: 'Switch to Telugu',
    body: 'Ask in Telugu and the answer comes back in Telugu. Ask in English and it stays in English, every time.',
    says: ['ఉద్యం వాతావరణం ఎలా ఉంది?', 'Telugu lo cheppu'],
  },
  {
    icon: BookOpen,
    title: 'Hear a story',
    body: 'A library of Telugu stories, narrated in full rather than summarised — built for reading to children.',
    says: ['కథ చెప్పు', 'Tell me a story'],
  },
]

export function UseCases() {
  return (
    <section id="uses" className="relative scroll-mt-20 py-24">
      <div className="mx-auto max-w-6xl px-5">
        <SectionHeading
          eyebrow="What you can use it for"
          title="Nine things you can say today"
          body="Every one of these is wired up and working — not a roadmap. The six marked
                for your own machine need SAIRA running on it; the rest work anywhere."
        />

        <div className="mt-14 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {USE_CASES.map((uc, i) => (
            <Effect
              key={uc.title}
              slide={{ direction: 'up', offset: 18 }}
              fade
              blur
              delay={(i % 3) * 0.08}
              inView
              inViewOnce
            >
              <Tilt maxTilt={6} className="h-full">
                <TiltContent className="group h-full rounded-2xl border border-border bg-card/40 p-6 transition-colors hover:border-brand/35 hover:bg-card/70">
                  <div className="flex size-10 items-center justify-center rounded-xl border border-brand/20 bg-brand/10 text-brand transition-shadow group-hover:shadow-[0_0_18px_-4px_var(--brand)]">
                    <uc.icon className="size-5" />
                  </div>

                  <h3 className="mt-5 text-base font-medium">{uc.title}</h3>
                  {uc.desktopOnly && (
                    <span className="mt-1.5 inline-block rounded border border-border px-1.5 py-0.5 font-mono text-[0.6rem] text-muted-foreground">
                      on your own machine
                    </span>
                  )}
                  <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{uc.body}</p>

                  <ul className="mt-5 space-y-1.5 border-t border-border pt-4">
                    {uc.says.map((s) => (
                      <li key={s} className="font-mono text-xs text-brand/80">
                        <span className="text-muted-foreground">&ldquo;</span>
                        {s}
                        <span className="text-muted-foreground">&rdquo;</span>
                      </li>
                    ))}
                  </ul>
                </TiltContent>
              </Tilt>
            </Effect>
          ))}
        </div>
      </div>
    </section>
  )
}
