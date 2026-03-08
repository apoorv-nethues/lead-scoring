import { useState } from 'react'
import { DataTable } from './components/DataTable'
import { ScorePanel } from './components/ScorePanel'
import { Glossary } from './components/Glossary'
import './App.css'

function App() {
  const [selectedRows, setSelectedRows] = useState<number[]>([])
  const [glossaryOpen, setGlossaryOpen] = useState(false)

  return (
    <div className="app">
      <header className="app-header">
        <h1>Lead Scoring Demo</h1>
        <button
          type="button"
          onClick={() => setGlossaryOpen(true)}
          className="btn-link"
        >
          Help & explanations
        </button>
      </header>
      <main className="app-main">
        <section className="section-data">
          <h2>Input data</h2>
          <DataTable
            selectedRows={selectedRows}
            onSelectRows={setSelectedRows}
          />
        </section>
        <section className="section-scores">
          <ScorePanel
            selectedRows={selectedRows}
            onClearSelection={() => setSelectedRows([])}
          />
        </section>
      </main>
      <Glossary open={glossaryOpen} onClose={() => setGlossaryOpen(false)} />
    </div>
  )
}

export default App
