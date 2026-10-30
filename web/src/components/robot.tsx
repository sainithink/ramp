import { motion, useReducedMotion } from 'motion/react'
import { cn } from '@/lib/utils'

export type RobotMood = 'idle' | 'listening' | 'thinking' | 'speaking' | 'error'

type RobotProps = {
  mood?: RobotMood
  className?: string
}

/**
 * The SAIRA face. Everything that moves is driven by `mood` so the robot shows
 * what the server is doing: the mouth bars only move while audio is playing,
 * the ring only spins while the model is thinking.
 */
export function Robot({ mood = 'idle', className }: RobotProps) {
  const reduced = useReducedMotion()
  const speaking = mood === 'speaking'
  const listening = mood === 'listening'
  const thinking = mood === 'thinking'

  const accent = mood === 'error' ? 'var(--destructive)' : 'var(--brand)'

  return (
    <div className={cn('relative grid place-items-center', className)}>
      {/* Halo — tightens when she is listening, flares while she talks. */}
      <motion.div
        aria-hidden
        className="absolute rounded-full"
        style={{
          width: '86%',
          height: '86%',
          background: `radial-gradient(circle, ${accent} 0%, transparent 68%)`,
        }}
        animate={reduced ? {} : { opacity: speaking ? 0.3 : listening ? 0.22 : 0.13 }}
        transition={{ type: 'spring', stiffness: 120, damping: 20 }}
      />

      {/* Thinking ring */}
      <motion.div
        aria-hidden
        className="absolute rounded-full border-2 border-transparent"
        style={{
          width: '94%',
          height: '94%',
          borderTopColor: accent,
          borderRightColor: `color-mix(in oklab, ${accent} 35%, transparent)`,
        }}
        animate={thinking && !reduced ? { rotate: 360 } : { rotate: 0, opacity: 0 }}
        transition={
          thinking
            ? { repeat: Infinity, ease: 'linear', duration: 1.6 }
            : { duration: 0.3 }
        }
      />

      {/* Listening pulse */}
      {listening && !reduced && (
        <motion.div
          aria-hidden
          className="absolute rounded-full border"
          style={{ width: '82%', height: '82%', borderColor: accent }}
          initial={{ scale: 0.86, opacity: 0.5 }}
          animate={{ scale: 1.14, opacity: 0 }}
          transition={{ repeat: Infinity, duration: 1.8, ease: 'easeOut' }}
        />
      )}

      <motion.svg
        viewBox="0 0 240 260"
        xmlns="http://www.w3.org/2000/svg"
        className="relative w-full"
        style={{ filter: `drop-shadow(0 0 18px color-mix(in oklab, ${accent} 35%, transparent))` }}
        animate={reduced ? {} : { y: [0, -6, 0] }}
        transition={{ repeat: Infinity, duration: 4, ease: 'easeInOut' }}
      >
        {/* antenna */}
        <line x1="120" y1="14" x2="120" y2="30" stroke={accent} strokeOpacity={0.4} strokeWidth={2} />
        <motion.circle
          cx="120"
          cy="11"
          r="4"
          fill={accent}
          animate={reduced ? {} : { opacity: [0.3, 1, 0.3] }}
          transition={{ repeat: Infinity, duration: 2.2, ease: 'easeInOut' }}
        />

        {/* ear pods */}
        <rect x="24" y="98" width="20" height="50" rx="9" fill="#06120d" stroke={accent} strokeOpacity={0.4} />
        <rect x="196" y="98" width="20" height="50" rx="9" fill="#06120d" stroke={accent} strokeOpacity={0.4} />
        <circle cx="34" cy="123" r="3.5" fill={accent} fillOpacity={0.35} />
        <circle cx="206" cy="123" r="3.5" fill={accent} fillOpacity={0.35} />

        {/* head */}
        <rect x="44" y="28" width="152" height="168" rx="46" fill="#081a12" stroke={accent} strokeWidth={1.6} />
        <path d="M60,74 Q120,54 180,74" fill="none" stroke={accent} strokeOpacity={0.3} />
        <circle cx="120" cy="46" r="3" fill={accent} fillOpacity={0.35} />

        {/* face plate */}
        <rect x="60" y="82" width="120" height="98" rx="30" fill="#05120c" stroke={accent} strokeOpacity={0.4} />

        {/* eyes — a slow blink, squinting a little while thinking */}
        <motion.g
          style={{ transformOrigin: '120px 115px' }}
          animate={reduced ? {} : { scaleY: thinking ? [1, 0.55, 1] : [1, 1, 0.1, 1] }}
          transition={
            thinking
              ? { repeat: Infinity, duration: 1.1, ease: 'easeInOut' }
              : { repeat: Infinity, duration: 5, times: [0, 0.92, 0.96, 1] }
          }
        >
          <ellipse cx="93" cy="115" rx="15" ry="10" fill={accent} />
          <ellipse cx="147" cy="115" rx="15" ry="10" fill={accent} />
          <circle cx="93" cy="115" r="4" fill="#04110b" />
          <circle cx="147" cy="115" r="4" fill="#04110b" />
        </motion.g>

        {/* cheek LEDs */}
        {[
          [72, 137], [82, 144], [92, 149], [148, 149], [158, 144], [168, 137],
          [76, 99], [164, 99], [104, 93], [136, 93],
        ].map(([cx, cy], i) => (
          <motion.circle
            key={`${cx}-${cy}`}
            cx={cx}
            cy={cy}
            r={cy === 99 || cy === 93 ? 2 : 2.4}
            fill={accent}
            animate={reduced ? { opacity: 0.3 } : { opacity: [0.18, 0.8, 0.18] }}
            transition={{ repeat: Infinity, duration: 2.4, delay: i * 0.12, ease: 'easeInOut' }}
          />
        ))}

        {/* mouth — bars rise and fall only while she is speaking */}
        <g transform="translate(0,-2)">
          {[
            [96, 158, 14], [104, 154, 22], [112, 151, 28], [120, 150, 30],
            [128, 151, 28], [136, 154, 22], [144, 158, 14],
          ].map(([x, y, h], i) => (
            <motion.rect
              key={x}
              x={x}
              y={y}
              width={4}
              height={h}
              rx={2}
              fill="var(--brand-soft)"
              style={{ transformOrigin: `${x + 2}px ${y + h / 2}px` }}
              animate={
                speaking && !reduced
                  ? { scaleY: [0.3, 1, 0.3] }
                  : { scaleY: listening ? 0.35 : 0.22 }
              }
              transition={
                speaking
                  ? { repeat: Infinity, duration: 0.45, delay: i * 0.06, ease: 'easeInOut' }
                  : { type: 'spring', stiffness: 200, damping: 22 }
              }
            />
          ))}
        </g>

        <line x1="104" y1="188" x2="136" y2="188" stroke={accent} strokeOpacity={0.25} />
        <rect x="100" y="196" width="40" height="16" rx="5" fill="#06120d" stroke={accent} strokeOpacity={0.4} />
        <path d="M56,254 Q60,218 100,210 L140,210 Q180,218 184,254 Z" fill="#081a12" stroke={accent} strokeWidth={1.6} />

        {/* chest badge */}
        <path d="M120,222 l16,9 v18 l-16,9 -16,-9 v-18 Z" fill="#05120c" stroke={accent} strokeOpacity={0.5} />
        <text
          x="120"
          y="246"
          textAnchor="middle"
          fill={accent}
          fontSize="15"
          fontFamily="Orbitron, sans-serif"
          fontWeight="700"
        >
          S
        </text>
      </motion.svg>
    </div>
  )
}
