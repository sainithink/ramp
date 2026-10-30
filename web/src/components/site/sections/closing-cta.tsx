import { Link } from 'react-router-dom'
import { ArrowRight } from 'lucide-react'
import { Effect } from '@animate-ui/react/primitives/effects/effect'
import { Magnetic } from '@animate-ui/react/primitives/effects/magnetic'
import { Button } from '@/components/ui/button'
import { Robot } from '@/components/robot'

export function ClosingCta() {
  return (
    <section className="relative overflow-hidden border-t border-border py-24">
      <div
        aria-hidden
        className="absolute inset-0 -z-10"
        style={{
          background:
            'radial-gradient(50% 60% at 50% 100%, color-mix(in oklab, var(--brand) 14%, transparent), transparent 70%)',
        }}
      />
      <div className="mx-auto max-w-2xl px-5 text-center">
        <Effect slide={{ direction: 'up', offset: 18 }} fade zoom inView inViewOnce>
          <Robot mood="listening" className="mx-auto w-32" />
        </Effect>

        <h2 className="mt-8 text-3xl font-semibold tracking-tight text-balance sm:text-4xl">
          Pick a name and start talking
        </h2>
        <p className="mt-4 text-muted-foreground text-pretty">
          Takes a minute. You choose what it answers to on the way in, and the first
          hundred conversations a month are free.
        </p>

        <div className="mt-8 flex justify-center">
          <Magnetic strength={0.28} range={160}>
            <Button size="lg" className="h-11 px-7 text-sm" asChild>
              <Link to="/register">
                Create your assistant
                <ArrowRight className="size-4" />
              </Link>
            </Button>
          </Magnetic>
        </div>
      </div>
    </section>
  )
}
