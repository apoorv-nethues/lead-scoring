import { useEffect, useState } from 'react'
import { fetchPreview, type DataRow } from '../api'
const DISPLAY_COLUMNS = [
  'row',
  'CURRENT_ENERGY_EFFICIENCY',
  'POTENTIAL_ENERGY_EFFICIENCY',
  'TOTAL_FLOOR_AREA',
  'PROPERTY_TYPE',
  'BUILT_FORM',
  'CONSTRUCTION_AGE_BAND',
  'TENURE',
  'epc_date',
]

interface DataTableProps {
  selectedRows: number[]
  onSelectRows: (rows: number[]) => void
}

export function DataTable({ selectedRows, onSelectRows }: DataTableProps) {
  const [data, setData] = useState<DataRow[]>([])
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [totalRows, setTotalRows] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

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

  if (loading) return <div className="data-table-loading">Loading data...</div>
  if (error) return <div className="data-table-error">Error: {error}</div>

  return (
    <div className="data-table-wrap">
      <div className="data-table-header">
        <span>
          Page {page} of {totalPages} ({totalRows} rows)
        </span>
        <button type="button" onClick={selectAllOnPage} className="btn-secondary">
          Select all on page
        </button>
      </div>
      <div className="table-scroll">
        <table className="data-table">
          <thead>
            <tr>
              <th></th>
              {DISPLAY_COLUMNS.map((col) => (
                <th key={col}>{col.replace(/_/g, ' ')}</th>
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
                {DISPLAY_COLUMNS.map((col) => (
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
        <span>
          Page {page} of {totalPages}
        </span>
        <button
          type="button"
          onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
          disabled={page >= totalPages}
        >
          Next
        </button>
      </div>
    </div>
  )
}
