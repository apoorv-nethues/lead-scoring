import { useEffect, useState } from 'react'
import { fetchPreview, type DataRow } from '../api'

const BASE_COLUMNS = [
  'row',
  'CURRENT_ENERGY_EFFICIENCY',
  'POTENTIAL_ENERGY_EFFICIENCY',
  'TOTAL_FLOOR_AREA',
  'PROPERTY_TYPE',
  'BUILT_FORM',
  'CONSTRUCTION_AGE_BAND',
  'TENURE',
  'epc_date',
  'label',
]

const GEO_COLUMNS = ['lsoa21cd', 'msoa21cd', 'ladcd']

const COLUMN_DISPLAY_NAMES: Record<string, string> = {
  row: 'Row',
  lsoa21cd: 'Neighbourhood',
  msoa21cd: 'District',
  ladcd: 'Council area',
  epc_date: 'EPC date',
  label: 'Label',
  CURRENT_ENERGY_EFFICIENCY: 'Current energy',
  POTENTIAL_ENERGY_EFFICIENCY: 'Potential energy',
  TOTAL_FLOOR_AREA: 'Floor area',
  PROPERTY_TYPE: 'Property type',
  BUILT_FORM: 'Built form',
  CONSTRUCTION_AGE_BAND: 'Construction age',
  TENURE: 'Tenure',
}

function getColumnLabel(col: string): string {
  return COLUMN_DISPLAY_NAMES[col] ?? col.replace(/_/g, ' ')
}

interface DataTableProps {
  selectedRows: number[]
  onSelectRows: (rows: number[]) => void
}

export function DataTable({ selectedRows, onSelectRows }: DataTableProps) {
  const [data, setData] = useState<DataRow[]>([])
  const [page, setPage] = useState(1)
  const [goToPageInput, setGoToPageInput] = useState('')
  const [totalPages, setTotalPages] = useState(1)
  const [totalRows, setTotalRows] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showGeoColumns, setShowGeoColumns] = useState(true)

  const epcIdx = BASE_COLUMNS.indexOf('epc_date')
  const displayColumns = [
    ...BASE_COLUMNS.slice(0, epcIdx),
    ...(showGeoColumns ? GEO_COLUMNS : []),
    ...BASE_COLUMNS.slice(epcIdx),
  ]

  useEffect(() => {
    setLoading(true)
    setError(null)
    fetchPreview(page, 50)
      .then((res) => {
        setData(res.rows)
        setTotalPages(res.total_pages)
        setTotalRows(res.total_rows)
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [page])

  const toggleRow = (rowNum: number) => {
    if (selectedRows.includes(rowNum)) {
      onSelectRows(selectedRows.filter((r) => r !== rowNum))
    } else {
      onSelectRows([...selectedRows, rowNum].sort((a, b) => a - b))
    }
  }

  const selectAllOnPage = () => {
    const pageRows = data.map((r) => r.row as number)
    const newSelection = [...new Set([...selectedRows, ...pageRows])].sort((a, b) => a - b)
    onSelectRows(newSelection)
  }

  const goToPage = () => {
    const n = parseInt(goToPageInput, 10)
    if (!isNaN(n) && n >= 1 && n <= totalPages) {
      setPage(n)
      setGoToPageInput('')
    }
  }

  const getPageNumbers = () => {
    const maxVisible = 5
    if (totalPages <= maxVisible) {
      return Array.from({ length: totalPages }, (_, i) => i + 1)
    }
    const half = Math.floor(maxVisible / 2)
    let start = Math.max(1, page - half)
    let end = Math.min(totalPages, start + maxVisible - 1)
    if (end - start + 1 < maxVisible) {
      start = Math.max(1, end - maxVisible + 1)
    }
    return Array.from({ length: end - start + 1 }, (_, i) => start + i)
  }

  if (loading) return <div className="data-table-loading">Loading data...</div>
  if (error) return <div className="data-table-error">Error: {error}</div>

  return (
    <div className="data-table-wrap">
      <div className="data-table-header">
        <span>
          Page {page} of {totalPages} ({totalRows} rows)
        </span>
        <div className="data-table-header-actions">
          <button
            type="button"
            onClick={() => setShowGeoColumns((v) => !v)}
            className={`btn-secondary btn-toggle ${showGeoColumns ? 'active' : ''}`}
            title={showGeoColumns ? 'Hide area columns' : 'Show area columns'}
          >
            {showGeoColumns ? 'Hide' : 'Show'} area columns
          </button>
          <button type="button" onClick={selectAllOnPage} className="btn-secondary">
            Select all on page
          </button>
        </div>
      </div>
      <div className="table-scroll">
        <table className="data-table">
          <thead>
            <tr>
              <th></th>
              {displayColumns.map((col) => (
                <th key={col}>{getColumnLabel(col)}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.map((row) => (
              <tr
                key={row.row}
                className={selectedRows.includes(row.row as number) ? 'selected' : ''}
                onClick={() => toggleRow(row.row as number)}
              >
                <td>
                  <input
                    type="checkbox"
                    checked={selectedRows.includes(row.row as number)}
                    onChange={() => toggleRow(row.row as number)}
                    onClick={(e) => e.stopPropagation()}
                  />
                </td>
                {displayColumns.map((col) => (
                  <td key={col}>{String(row[col] ?? '')}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="data-table-pagination">
        <button
          type="button"
          onClick={() => setPage((p) => Math.max(1, p - 1))}
          disabled={page <= 1}
        >
          Previous
        </button>
        <div className="pagination-pages">
          {getPageNumbers().map((n) => (
            <button
              key={n}
              type="button"
              onClick={() => setPage(n)}
              className={`pagination-page-btn ${n === page ? 'current' : ''}`}
            >
              {n}
            </button>
          ))}
        </div>
        <button
          type="button"
          onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
          disabled={page >= totalPages}
        >
          Next
        </button>
        <div className="pagination-goto">
          <span>Go to</span>
          <input
            type="number"
            min={1}
            max={totalPages}
            value={goToPageInput}
            onChange={(e) => setGoToPageInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && goToPage()}
            placeholder={String(page)}
            className="pagination-goto-input"
          />
          <button type="button" onClick={goToPage} className="btn-secondary">
            Go
          </button>
        </div>
      </div>
    </div>
  )
}
