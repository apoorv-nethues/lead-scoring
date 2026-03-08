import { useEffect, useState } from 'react'
import { fetchGlossary, type Glossary as GlossaryType } from '../api'

interface GlossaryProps {
  open: boolean
  onClose: () => void
}

export function Glossary({ open, onClose }: GlossaryProps) {
  const [glossary, setGlossary] = useState<GlossaryType | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (open && !glossary) {
      setLoading(true)
      fetchGlossary()
        .then(setGlossary)
        .finally(() => setLoading(false))
    }
  }, [open, glossary])

  if (!open) return null

  return (
    <div className="glossary-overlay" onClick={onClose}>
      <div className="glossary-modal" onClick={(e) => e.stopPropagation()}>
        <div className="glossary-header">
          <h2>Help & explanations</h2>
          <button type="button" onClick={onClose} className="glossary-close">
            ×
          </button>
        </div>
        {loading ? (
          <div className="glossary-loading">Loading...</div>
        ) : glossary ? (
          <div className="glossary-content">
            <section>
              <h3>Columns</h3>
              <dl>
                {glossary.columns.map((c) => (
                  <div key={c.name}>
                    <dt>{c.displayName || c.name.replace(/_/g, ' ')}</dt>
                    <dd>{c.description}</dd>
                  </div>
                ))}
              </dl>
            </section>
            {glossary.areaProfileExplanation && (
              <section>
                <h3>Area & owner profile</h3>
                <p>{glossary.areaProfileExplanation}</p>
              </section>
            )}
            <section>
              <h3>Model metrics</h3>
              <dl>
                {glossary.metrics.map((m) => (
                  <div key={m.name}>
                    <dt>{m.name}</dt>
                    <dd>{m.description}</dd>
                  </div>
                ))}
              </dl>
            </section>
            <section>
              <h3>Focus C vs Focus E</h3>
              <p>{glossary.focusExplanation}</p>
            </section>
          </div>
        ) : null}
      </div>
    </div>
  )
}
