import { useState, useEffect } from 'react'

const API_BASE = 'http://127.0.0.1:8000'

function AlertsPage() {
    const [alerts, setAlerts] = useState([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)

    useEffect(() => {
        fetch(`${API_BASE}/alerts?limit=100`)
            .then((res) => {
                if (!res.ok) throw new Error(`API returned ${res.status}`)
                return res.json()
            })
            .then((data) => {
                setAlerts(data)
                setLoading(false)
            })
            .catch((err) => {
                setError(err.message)
                setLoading(false)
            })
    }, [])

    if (loading) return <div className="status">Loading alerts...</div>
    if (error) {
        return (
            <div className="status error">
                <p>Failed to load alerts: {error}</p>
                <p>
                    Check that the API is running (<code>uvicorn src.api.main:app --reload</code>)
                    and that CORS is configured to allow <code>http://localhost:5173</code>.
                </p>
            </div>
        )
    }

    return (
        <div>
            <p className="subtitle">{alerts.length} alert(s)</p>
            <table className="data-table">
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Type</th>
                        <th>Message</th>
                        <th>Similarity</th>
                        <th>Created At</th>
                    </tr>
                </thead>
                <tbody>
                    {alerts.map((alert) => (
                        <tr key={alert.id}>
                            <td>{alert.id}</td>
                            <td><span className={`badge badge-${alert.type}`}>{alert.type}</span></td>
                            <td>{alert.message}</td>
                            <td>{alert.similarity != null ? alert.similarity.toFixed(3) : '—'}</td>
                            <td>{new Date(alert.created_at).toLocaleString()}</td>
                        </tr>
                    ))}
                </tbody>
            </table>
            {alerts.length === 0 && (
                <p className="status">No alerts yet — run a pipeline script to generate some.</p>
            )}
        </div>
    )
}

export default AlertsPage