import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion'
import { SectionHeading } from '@/components/site/section-heading'

const QA = [
  {
    q: 'Is my microphone always sending audio somewhere?',
    a: 'The microphone is open in your browser, but audio is only acted on once the wake name is heard. In always-on mode you turn that gate off deliberately, and even then the audio goes to our own server and nowhere else.',
  },
  {
    q: 'Which AI service is behind it?',
    a: 'None. Speech recognition runs on Whisper, the answers come from Llama 3.2 and the voice is Kokoro — all three run on the same machine that serves this page. There is no OpenAI, Anthropic or Google key in the stack.',
  },
  {
    q: 'Can other people see my conversations?',
    a: 'No. Each account has its own encryption key, derived separately for memories, preferences and profile, so one account cannot read another even with database access. Administrators can see how many conversations you have had and change your limit — never the contents.',
  },
  {
    q: 'What if I pick a name that sounds like an ordinary word?',
    a: 'Names shorter than three letters are refused for that reason, and common words are filtered out of wake matching. Longer, more distinctive names work best — but the matching is phonetic, so near-misses in the transcript still wake it.',
  },
  {
    q: 'Does it really speak Telugu?',
    a: 'Yes, both ways. Ask in Telugu and the reply comes back in Telugu with a Telugu voice. The reply is also checked against the script you asked in, so an older English memory cannot bleed into a Telugu answer.',
  },
  {
    q: 'What happens when I hit the free limit?',
    a: 'It tells you, and stops before spending any model time. Nothing is deleted, and the count resets at the start of the next month. Paid plans with higher limits are coming.',
  },
  {
    q: 'Can I change the name after signing up?',
    a: 'Any time, from the assistant page. The change takes effect on the next thing you say — no restart, no re-training.',
  },
]

export function Faq() {
  return (
    <section id="faq" className="relative scroll-mt-20 border-t border-border py-24">
      <div className="mx-auto max-w-3xl px-5">
        <SectionHeading eyebrow="FAQ" title="Questions worth asking" />

        <Accordion type="single" collapsible className="mt-12">
          {QA.map((item) => (
            <AccordionItem key={item.q} value={item.q}>
              <AccordionTrigger className="text-left text-base">{item.q}</AccordionTrigger>
              <AccordionContent className="text-sm leading-relaxed text-muted-foreground">
                {item.a}
              </AccordionContent>
            </AccordionItem>
          ))}
        </Accordion>
      </div>
    </section>
  )
}
