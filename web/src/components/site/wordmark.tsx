import { Link } from 'react-router-dom'
import { cn } from '@/lib/utils'

/** The S.A.I.R.A lockup: Orbitron, wide tracking, dimmed separators. */
export function Wordmark({ className, to = '/' }: { className?: string; to?: string }) {
  return (
    <Link
      to={to}
      className={cn('wordmark text-sm text-brand transition-opacity hover:opacity-80', className)}
      aria-label="SAIRA home"
    >
      {'SAIRA'.split('').map((ch, i) => (
        <span key={i}>
          {ch}
          {i < 4 && <span className="text-foreground/30">.</span>}
        </span>
      ))}
    </Link>
  )
}
