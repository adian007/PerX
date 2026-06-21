import { Link } from 'react-router-dom'

export function PublicNav() {
  return (
    <nav className="sticky top-0 z-50 border-b border-border bg-cream">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-6 py-4">
        <Link to="/" className="font-display text-2xl font-semibold italic text-ink">
          PerX
        </Link>
      </div>
    </nav>
  )
}
