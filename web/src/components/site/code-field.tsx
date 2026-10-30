import { InputOTP, InputOTPGroup, InputOTPSlot } from '@/components/ui/input-otp'

type Props = {
  value: string
  onChange: (value: string) => void
  onComplete?: (value: string) => void
  disabled?: boolean
}

/** The six-digit code from the email. */
export function CodeField({ value, onChange, onComplete, disabled }: Props) {
  return (
    <InputOTP
      maxLength={6}
      value={value}
      onChange={onChange}
      onComplete={onComplete}
      disabled={disabled}
      containerClassName="justify-center"
      autoFocus
    >
      <InputOTPGroup>
        {[0, 1, 2, 3, 4, 5].map((i) => (
          <InputOTPSlot key={i} index={i} className="size-12 text-lg" />
        ))}
      </InputOTPGroup>
    </InputOTP>
  )
}
