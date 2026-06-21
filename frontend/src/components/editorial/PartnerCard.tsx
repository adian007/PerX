import { ExternalLink, MapPin } from 'lucide-react'
import type { Partner } from '@/data/mockPartners'
import { PARTNER_CATEGORIES } from '@/data/mockPartners'

interface PartnerCardProps {
  partner: Partner
}

export function PartnerCard({ partner }: PartnerCardProps) {
  const categoryLabel = PARTNER_CATEGORIES[partner.category]

  return (
    <article className="flex h-full flex-col border border-[#1A1A1A]/12 bg-paper p-8 md:p-10">
      <div className="flex items-start justify-between gap-4">
        <p className="font-mono text-xs uppercase tracking-[0.2em] text-sienna">{categoryLabel}</p>
        {partner.highlight && (
          <span className="shrink-0 border border-[#1A1A1A]/12 px-2 py-0.5 font-mono text-[10px] uppercase tracking-wide text-muted">
            {partner.highlight}
          </span>
        )}
      </div>

      <h3 className="mt-4 font-display text-2xl font-semibold md:text-3xl">{partner.name}</h3>
      <p className="mt-2 font-display text-lg italic text-muted">{partner.tagline}</p>

      <p className="mt-5 flex-1 text-base leading-relaxed text-muted md:text-lg">{partner.perkOffer}</p>

      <div className="mt-6 flex flex-wrap items-center justify-between gap-3 border-t border-[#1A1A1A]/12 pt-5">
        <p className="flex items-center gap-1.5 text-sm text-muted">
          <MapPin className="size-3.5 shrink-0" strokeWidth={1.5} aria-hidden />
          {partner.location}
        </p>
        {partner.externalUrl && (
          <a
            href={partner.externalUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-sm uppercase tracking-wide text-ink underline-offset-4 hover:underline"
          >
            Hap
            <ExternalLink className="size-3.5" strokeWidth={1.5} aria-hidden />
          </a>
        )}
      </div>
    </article>
  )
}
