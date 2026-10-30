import { Link } from 'react-router-dom'
import { Check } from 'lucide-react'
import { Effect } from '@animate-ui/react/primitives/effects/effect'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { SectionHeading } from '@/components/site/section-heading'
import { cn } from '@/lib/utils'

const PLANS = [
  {
    name: 'Free',
    price: '₹0',
    cadence: 'forever',
    blurb: 'Everything works. The only cap is how much you talk.',
    cta: 'Create an account',
    featured: false,
    perks: [
      '100 conversations a month',
      'Your own assistant name',
      'Encrypted memory and preferences',
      'English and Telugu',
      'Every tool — music, apps, weather, stories',
    ],
  },
  {
    name: 'Pro',
    price: 'Soon',
    cadence: '',
    blurb: 'For when a hundred a month stops being enough.',
    cta: 'Start free, upgrade later',
    featured: true,
    perks: [
      '5,000 conversations a month',
      'Everything in Free',
      'Longer memory recall',
      'Priority on the inference queue',
    ],
  },
]

export function Pricing() {
  return (
    <section id="pricing" className="relative scroll-mt-20 border-t border-border py-24">
      <div className="mx-auto max-w-6xl px-5">
        <SectionHeading
          eyebrow="Pricing"
          title="Free to start, properly free"
          body="No trial clock, no card. The free tier is the whole assistant with a monthly conversation cap."
        />

        <div className="mx-auto mt-14 grid max-w-3xl gap-5 sm:grid-cols-2">
          {PLANS.map((plan, i) => (
            <Effect
              key={plan.name}
              slide={{ direction: 'up', offset: 18 }}
              fade
              zoom={{ initialScale: 0.97 }}
              delay={i * 0.1}
              inView
              inViewOnce
            >
              <div
                className={cn(
                  'relative flex h-full flex-col rounded-2xl border p-7',
                  plan.featured
                    ? 'border-brand/40 bg-brand/[0.04] shadow-[0_0_60px_-20px_var(--brand)]'
                    : 'border-border bg-card/40',
                )}
              >
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-medium tracking-wide uppercase">{plan.name}</h3>
                  {plan.featured && <Badge variant="outline" className="border-brand/40 text-brand">Planned</Badge>}
                </div>

                <div className="mt-5 flex items-baseline gap-1.5">
                  <span className="font-display text-4xl font-bold">{plan.price}</span>
                  {plan.cadence && (
                    <span className="text-sm text-muted-foreground">/ {plan.cadence}</span>
                  )}
                </div>

                <p className="mt-3 text-sm text-muted-foreground">{plan.blurb}</p>

                <ul className="mt-6 flex-1 space-y-2.5">
                  {plan.perks.map((perk) => (
                    <li key={perk} className="flex items-start gap-2.5 text-sm">
                      <Check className="mt-0.5 size-4 shrink-0 text-brand" />
                      <span className="text-muted-foreground">{perk}</span>
                    </li>
                  ))}
                </ul>

                <Button
                  className="mt-7 h-10"
                  variant={plan.featured ? 'outline' : 'default'}
                  asChild
                >
                  <Link to="/register">{plan.cta}</Link>
                </Button>
              </div>
            </Effect>
          ))}
        </div>
      </div>
    </section>
  )
}
