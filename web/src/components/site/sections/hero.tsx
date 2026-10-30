import { Link } from 'react-router-dom'
import { ArrowRight, Mic } from 'lucide-react'
import { Effect } from '@animate-ui/react/primitives/effects/effect'
import { SplittingText } from '@animate-ui/react/primitives/texts/splitting'
import { RotatingText, RotatingTextContainer } from '@animate-ui/react/primitives/texts/rotating'
import { StarsBackground } from '@/components/animate-ui/backgrounds/stars'
import { Button } from '@/components/ui/button'
import { Robot } from '@/components/robot'
import { DemoExchange } from './demo-exchange'

const ASKS = [
  'play Arijit Singh on YouTube',
  'what’s the weather in Hyderabad',
  'open sainith.in',
  'turn the volume down',
  'కథ చెప్పు',
  'call me Sai from now on',
]

export function Hero() {
  return (
    <section className="relative isolate overflow-hidden">
      <StarsBackground
        className="absolute inset-0 -z-10"
        starColor="#8affc4"
        factor={0.03}
      />
      {/* An emerald bloom rising from behind the robot. */}
      <div
        aria-hidden
        className="absolute inset-x-0 top-0 -z-10 h-[680px] opacity-70"
        style={{
          background:
            'radial-gradient(60% 50% at 50% 0%, color-mix(in oklab, var(--brand) 16%, transparent), transparent 70%)',
        }}
      />

      <div className="mx-auto grid max-w-6xl items-center gap-12 px-5 pt-32 pb-20 lg:grid-cols-[1.05fr_0.95fr] lg:pt-40 lg:pb-28">
        <div>
          <Effect slide={{ direction: 'up', offset: 14 }} fade blur inView>
            <span className="inline-flex items-center gap-2 rounded-full border border-brand/25 bg-brand/8 px-3 py-1 text-xs text-brand">
              <Mic className="size-3" />
              Runs on our own hardware — not a cloud AI service
            </span>
          </Effect>

          <h1 className="mt-6 text-4xl leading-[1.05] font-semibold tracking-tight text-balance sm:text-5xl lg:text-6xl">
            <SplittingText
              text="A voice assistant that"
              type="words"
              stagger={0.045}
              className="inline"
            />{' '}
            <span className="bg-gradient-to-br from-brand via-brand-soft to-brand bg-clip-text text-transparent">
              <SplittingText text="answers to your name" type="words" stagger={0.045} delay={0.3} />
            </span>
          </h1>

          <p className="mt-6 max-w-xl text-base text-muted-foreground sm:text-lg">
            Talk to it the way you would to a person. It hears you, thinks on hardware
            you control, speaks back, and remembers what you told it last week —
            under whatever name you pick for it.
          </p>

          {/* The phrases differ in length, so the row keeps a fixed height and
              the closing quote rides along rather than being pushed about. */}
          <div className="mt-7 flex h-12 items-center font-mono text-sm text-muted-foreground sm:h-6">
            <span className="shrink-0 text-brand">&ldquo;Hey Saira,&nbsp;</span>
            <RotatingTextContainer
              text={ASKS}
              duration={2600}
              className="min-w-0 text-foreground"
            >
              <RotatingText className="truncate" />
            </RotatingTextContainer>
            <span className="shrink-0 text-brand">&rdquo;</span>
          </div>

          <div className="mt-9 flex flex-col gap-3 sm:flex-row">
            <Button size="lg" className="h-11 px-6 text-sm" asChild>
              <Link to="/register">
                Create a free account
                <ArrowRight className="size-4" />
              </Link>
            </Button>
            <Button size="lg" variant="outline" className="h-11 px-6 text-sm" asChild>
              <Link to="/login">I already have one</Link>
            </Button>
          </div>

          <p className="mt-4 text-xs text-muted-foreground">
            100 conversations a month, free. No card, no third-party AI service.
          </p>
        </div>

        <Effect slide={{ direction: 'up', offset: 24 }} fade zoom delay={0.15} inView>
          <div className="relative">
            <Robot mood="speaking" className="mx-auto w-52 sm:w-60" />
            <DemoExchange className="mt-6" />
          </div>
        </Effect>
      </div>
    </section>
  )
}
