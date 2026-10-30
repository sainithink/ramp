import { useEffect } from 'react'
import { ScrollProgress, ScrollProgressProvider } from '@animate-ui/react/primitives/scroll-progress'
import { SiteNav } from '@/components/site/site-nav'
import { SiteFooter } from '@/components/site/site-footer'
import { Hero } from '@/components/site/sections/hero'
import { UseCases } from '@/components/site/sections/use-cases'
import { HowItWorks } from '@/components/site/sections/how-it-works'
import { Features } from '@/components/site/sections/features'
import { Pricing } from '@/components/site/sections/pricing'
import { Faq } from '@/components/site/sections/faq'
import { ClosingCta } from '@/components/site/sections/closing-cta'

export default function LandingPage() {
  // The sections mount after the browser has already handled the URL fragment,
  // so a shared link like /#pricing has to be scrolled to by hand.
  useEffect(() => {
    const id = decodeURIComponent(window.location.hash.slice(1))
    if (!id) return
    const target = document.getElementById(id)
    if (target) requestAnimationFrame(() => target.scrollIntoView())
  }, [])

  return (
    <ScrollProgressProvider global>
      <ScrollProgress
        mode="scaleX"
        className="fixed inset-x-0 top-0 z-[60] h-0.5 origin-left bg-brand"
      />
      <SiteNav />
      <main>
        <Hero />
        <UseCases />
        <HowItWorks />
        <Features />
        <Pricing />
        <Faq />
        <ClosingCta />
      </main>
      <SiteFooter />
    </ScrollProgressProvider>
  )
}
