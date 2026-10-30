import { Link } from 'react-router-dom'
import { Wordmark } from './wordmark'

const STACK = [
  ['Language model', 'Llama 3.2 · local'],
  ['Speech to text', 'Whisper'],
  ['Voice', 'Kokoro ONNX'],
  ['Storage', 'Encrypted per account'],
]

export function SiteFooter() {
  return (
    <footer className="border-t border-border">
      <div className="mx-auto max-w-6xl px-5 py-14">
        <div className="grid gap-10 md:grid-cols-[1.4fr_1fr_1fr]">
          <div>
            <Wordmark />
            <p className="mt-4 max-w-xs text-sm text-muted-foreground">
              A voice assistant that runs on hardware you control, answers to a name
              you choose, and keeps what you tell it encrypted per account.
            </p>
          </div>

          <div>
            <h3 className="text-xs font-medium tracking-widest text-muted-foreground uppercase">
              Product
            </h3>
            <ul className="mt-4 space-y-2.5 text-sm">
              <li><a href="#uses" className="text-muted-foreground hover:text-foreground">What it does</a></li>
              <li><a href="#how" className="text-muted-foreground hover:text-foreground">How it works</a></li>
              <li><a href="#pricing" className="text-muted-foreground hover:text-foreground">Pricing</a></li>
              <li><Link to="/register" className="text-muted-foreground hover:text-foreground">Create an account</Link></li>
            </ul>
          </div>

          <div>
            <h3 className="text-xs font-medium tracking-widest text-muted-foreground uppercase">
              Running on
            </h3>
            <ul className="mt-4 space-y-2.5 text-sm">
              {STACK.map(([k, v]) => (
                <li key={k} className="flex flex-col">
                  <span className="text-muted-foreground">{k}</span>
                  <span className="font-mono text-xs text-brand/80">{v}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>

        <div className="mt-12 flex flex-col gap-3 border-t border-border pt-6 text-xs text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
          <span>Sainithin Artificial Intelligence Response Assistant</span>
          <span className="font-mono">Self-hosted · no third-party AI service</span>
        </div>
      </div>
    </footer>
  )
}
