import type { ReactNode } from 'react'
import { AnimatePresence, motion } from 'motion/react'
import { AlertCircle } from 'lucide-react'

/** A form-level error that slides in rather than jumping the layout. */
export function FormError({ children }: { children: ReactNode }) {
  return (
    <AnimatePresence initial={false}>
      {children ? (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          exit={{ opacity: 0, height: 0 }}
          transition={{ type: 'spring', stiffness: 320, damping: 32 }}
          className="overflow-hidden"
        >
          <div
            role="alert"
            className="flex items-start gap-2.5 rounded-lg border border-destructive/40 bg-destructive/10 px-3 py-2.5 text-sm text-destructive"
          >
            <AlertCircle className="mt-0.5 size-4 shrink-0" />
            <span>{children}</span>
          </div>
        </motion.div>
      ) : null}
    </AnimatePresence>
  )
}
