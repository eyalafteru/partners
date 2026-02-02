'use client'

import { useState, useEffect } from 'react'
import { Database, RefreshCw, Download, ChevronRight, Play } from 'lucide-react'

interface TableInfo {
  name: string
  row_count: number
}

interface ColumnInfo {
  name: string
  type: string
  nullable: boolean
  primary_key: boolean
}

export default function DatabaseExplorerPage() {
  const [tables, setTables] = useState<TableInfo[]>([])
  const [selectedTable, setSelectedTable] = useState<string>('')
  const [columns, setColumns] = useState<ColumnInfo[]>([])
  const [rows, setRows] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [customQuery, setCustomQuery] = useState('')
  const [queryResult, setQueryResult] = useState<any>(null)
  const [showQuery, setShowQuery] = useState(false)

  useEffect(() => {
    fetchTables()
  }, [])

  useEffect(() => {
    if (selectedTable) {
      fetchTableData()
    }
  }, [selectedTable, page])

  const fetchTables = async () => {
    try {
      const response = await fetch('/api/admin/database/tables')
      if (response.ok) {
        const data = await response.json()
        setTables(data)
      }
    } catch (error) {
      console.error('Failed to fetch tables:', error)
    } finally {
      setLoading(false)
    }
  }

  const fetchTableData = async () => {
    try {
      const response = await fetch(
        `/api/admin/database/tables/${selectedTable}?page=${page}&per_page=20`
      )
      if (response.ok) {
        const data = await response.json()
        setColumns(data.columns)
        setRows(data.rows)
        setTotalPages(data.pages)
      }
    } catch (error) {
      console.error('Failed to fetch table data:', error)
    }
  }

  const runQuery = async () => {
    try {
      const response = await fetch('/api/admin/database/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: customQuery })
      })
      
      if (response.ok) {
        const data = await response.json()
        setQueryResult(data)
      } else {
        const error = await response.json()
        setQueryResult({ error: error.detail })
      }
    } catch (error) {
      setQueryResult({ error: 'שגיאה בהרצת השאילתה' })
    }
  }

  const exportCSV = () => {
    if (!rows.length) return
    
    const headers = columns.map(c => c.name).join(',')
    const data = rows.map(row => 
      columns.map(c => JSON.stringify(row[c.name] ?? '')).join(',')
    ).join('\n')
    
    const csv = `${headers}\n${data}`
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${selectedTable}.csv`
    a.click()
  }

  return (
    <div className="h-full flex">
      {/* רשימת טבלאות */}
      <div className="w-64 border-l border-gray-200 bg-white overflow-hidden flex flex-col">
        <div className="p-4 border-b border-gray-200">
          <h2 className="font-semibold flex items-center gap-2">
            <Database className="w-5 h-5" />
            טבלאות
          </h2>
        </div>
        
        <div className="flex-1 overflow-auto">
          {loading ? (
            <div className="p-4 text-center text-gray-500">טוען...</div>
          ) : (
            tables.map((table) => (
              <button
                key={table.name}
                onClick={() => { setSelectedTable(table.name); setPage(1) }}
                className={`w-full p-3 text-right border-b border-gray-100 hover:bg-gray-50 flex items-center justify-between ${
                  selectedTable === table.name ? 'bg-primary-50' : ''
                }`}
              >
                <span className="font-medium text-sm">{table.name}</span>
                <span className="text-xs text-gray-500">{table.row_count}</span>
              </button>
            ))
          )}
        </div>
      </div>

      {/* תוכן */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {!selectedTable ? (
          <div className="flex-1 flex items-center justify-center text-gray-500">
            <div className="text-center">
              <Database className="w-16 h-16 mx-auto mb-4 opacity-50" />
              <p>בחר טבלה לצפייה</p>
            </div>
          </div>
        ) : (
          <>
            {/* כותרת */}
            <div className="bg-white border-b border-gray-200 p-4 flex items-center justify-between">
              <div>
                <h3 className="font-semibold">{selectedTable}</h3>
                <p className="text-sm text-gray-500">
                  {rows.length} רשומות מוצגות
                </p>
              </div>
              <div className="flex gap-2">
                <button onClick={fetchTableData} className="btn btn-secondary">
                  <RefreshCw className="w-4 h-4" />
                </button>
                <button onClick={exportCSV} className="btn btn-secondary flex items-center gap-2">
                  <Download className="w-4 h-4" />
                  CSV
                </button>
              </div>
            </div>

            {/* טבלה */}
            <div className="flex-1 overflow-auto">
              <table className="w-full border-collapse">
                <thead className="bg-gray-50 sticky top-0">
                  <tr>
                    {columns.map((col) => (
                      <th key={col.name} className="text-right px-4 py-3 text-sm font-medium text-gray-500 border-b">
                        <div className="flex items-center gap-1">
                          {col.primary_key && <span className="text-yellow-500">🔑</span>}
                          {col.name}
                        </div>
                        <span className="text-xs text-gray-400">{col.type}</span>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {rows.map((row, i) => (
                    <tr key={i} className="hover:bg-gray-50">
                      {columns.map((col) => (
                        <td key={col.name} className="px-4 py-2 text-sm max-w-xs truncate">
                          {typeof row[col.name] === 'object' 
                            ? JSON.stringify(row[col.name]).slice(0, 50) + '...'
                            : String(row[col.name] ?? '-')
                          }
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="bg-white border-t border-gray-200 p-4 flex items-center justify-center gap-2">
                <button
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="btn btn-secondary"
                >
                  הקודם
                </button>
                <span className="text-gray-600">
                  עמוד {page} מתוך {totalPages}
                </span>
                <button
                  onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
                  className="btn btn-secondary"
                >
                  הבא
                </button>
              </div>
            )}
          </>
        )}

        {/* SQL Query */}
        <div className="bg-white border-t border-gray-200">
          <button 
            onClick={() => setShowQuery(!showQuery)}
            className="w-full p-3 text-right flex items-center gap-2 hover:bg-gray-50"
          >
            <ChevronRight className={`w-4 h-4 transition-transform ${showQuery ? 'rotate-90' : ''}`} />
            שאילתת SQL
          </button>
          
          {showQuery && (
            <div className="p-4 border-t border-gray-100">
              <textarea
                className="input font-mono text-sm h-24 mb-2"
                value={customQuery}
                onChange={(e) => setCustomQuery(e.target.value)}
                placeholder="SELECT * FROM leads WHERE status = 'matched' LIMIT 10;"
              />
              <div className="flex items-center gap-2 mb-4">
                <button onClick={runQuery} className="btn btn-primary flex items-center gap-2">
                  <Play className="w-4 h-4" />
                  הרץ
                </button>
                <span className="text-xs text-gray-500">⚠️ רק SELECT מותר</span>
              </div>
              
              {queryResult && (
                <div className="bg-gray-50 rounded-lg p-4 overflow-auto max-h-48">
                  {queryResult.error ? (
                    <span className="text-danger-600">{queryResult.error}</span>
                  ) : (
                    <pre className="text-xs">{JSON.stringify(queryResult.rows?.slice(0, 5), null, 2)}</pre>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
