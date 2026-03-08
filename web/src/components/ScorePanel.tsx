import { useState } from 'react'
import { predict, type Prediction } from '../api'

interface ScorePanelProps {
  selectedRows: number[]
  onClearSelection: () => void
}

export function ScorePanel({ selectedRows, onClearSelection }: ScorePanelProps) {
  const [predictions, setPredictions] = useState<Prediction[] | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleGetScore = async () => {
    if (selectedRows.length === 0) return
    setLoading(true)
    setError(null)
    setPredictions(null)
    try {
      const res = await predict(selectedRows)
      setPredictions(res.predictions)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="score-panel">
      <h3>Predicted scores</h3>
      {selectedRows.length > 0 ? (
        <>
          <p className="score-panel-hint">
            {selectedRows.length} row(s) selected. Click "Get score" to predict.
          </p>
          <div className="score-panel-actions">
            <button
              type="button"
              onClick={handleGetScore}
              disabled={loading}
              className="btn-primary"
            >
              {loading ? 'Loading...' : 'Get score'}
            </button>
            <button type="button" onClick={onClearSelection} className="btn-secondary">
              Clear selection
            </button>
          </div>
        </>
      ) : (
        <p className="score-panel-hint">Select one or more rows from the table above.</p>
      )}
      {error && <div className="score-panel-error">{error}</div>}
      {predictions && predictions.length > 0 && (
        <div className="score-results">
          <table className="score-table">
            <thead>
              <tr>
                <th>Row</th>
                <th>Focus C</th>
                <th>Focus E</th>
              </tr>
            </thead>
            <tbody>
              {predictions.map((p) => (
                <tr key={p.row}>
                  <td>{p.row}</td>
                  <td>{(p.score_focus_c * 100).toFixed(2)}%</td>
                  <td>{(p.score_focus_e * 100).toFixed(2)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
