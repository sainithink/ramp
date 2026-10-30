import { Effect } from '@animate-ui/react/primitives/effects/effect'
import { cn } from '@/lib/utils'

type Props = {
  eyebrow?: string
  title: string
  body?: string
  align?: 'left' | 'center'
  className?: string
}

export function SectionHeading({ eyebrow, title, body, align = 'center', className }: Props) {
  return (
    <Effect slide={{ direction: 'up', offset: 14 }} fade blur inView inViewOnce>
      <div
        className={cn(
          'max-w-2xl',
          align === 'center' && 'mx-auto text-center',
          className,
        )}
      >
        {eyebrow && (
          <span className="font-mono text-xs tracking-[0.2em] text-brand uppercase">
            {eyebrow}
          </span>
        )}
        <h2 className="mt-3 text-3xl font-semibold tracking-tight text-balance sm:text-4xl">
          {title}
        </h2>
        {body && (
          <p className="mt-4 text-base text-pretty text-muted-foreground">{body}</p>
        )}
      </div>
    </Effect>
  )
}
