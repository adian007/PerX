/** English copy for the AI chat drawer (Gemma2:2b responds better in English). */

export const chatEn = {
  title: 'PerX Consultant',
  subtitle: 'Answers based on your profile and budget',
  hello: 'Hello',
  intro: "I'm PerX. Ask about your budget, recommendations, or benefit choices.",
  thinking: 'PerX is thinking…',
  placeholder: 'Ask about your benefits…',
  unavailable:
    'PerX is unavailable. Make sure the backend and Ollama (gemma2:2b) are running.',
  via: 'via',
  send: 'Send',
  promptHsa: 'How does employer health coverage work?',
  promptBudget: 'How much wellness budget do I have left?',
  promptRecommend: 'Why were these benefits recommended for me?',
  promptCompare: 'Compare gym membership vs home fitness',
  promptWishlist: 'What perks have I saved?',
  promptJourney: 'How is my benefit path progress?',
  budgetReply: (
    remaining: string,
    currency: string,
    allocated: string,
    spent: string,
  ) =>
    `You have ${remaining} remaining this period (${currency}). Allocated: ${allocated}. Spent: ${spent}.`,
} as const

export const CHAT_SAMPLE_PROMPTS = [
  chatEn.promptBudget,
  chatEn.promptRecommend,
  chatEn.promptWishlist,
  chatEn.promptJourney,
] as const
