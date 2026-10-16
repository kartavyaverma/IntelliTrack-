import { useState, useEffect, useCallback } from 'react'
import { getJSON, API_HINT } from '../api'

const POLL_INTERVAL_MS = 5000 // check for new alerts every 5 seconds

function AlertsPage() {
    const [alerts, setAlerts] = useState([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)
    const [lastUpdated, setLastUpdated] = useState(null)

    const fetchAlerts = useCallback(() => {
        getJSON('/alerts?limit=100')
            .then((data) => {
                setAlerts(data)
                setError(null)
                setLastUpdated(new Date())
            })
            .catch((err) => setError(err.message))
            .finally(() => setLoading(false))
    }, [])

    useEffect(() => {
        fetchAlerts() // initial load
        const interval = setInterval(fetchAlerts, POLL_INTERVAL_MS)
        return () => clearInterval(interval) // stop polling when leaving this tab
    }, [fetchAlerts])

    return (
        <div>
            <div className="toolbar">
                <span className="count">{alerts.length} alert(s)</span>
                <span className="spacer" />
                {lastUpdated && (
                    <span className="last-updated">Updated {lastUpdated.toLocaleTimeString()}</span>
                )}
                <button className="btn" onClick={fetchAlerts}>Refresh</button>
            </div>

            {loading && <div className="status">Loading alerts...</div>}
            {error && (
                <div className="status error">
                    <p>Failed to load alerts: {error}</p>
                    <p>{API_HINT}</p>
                </div>
            )}

            {!loading && !error && alerts.length === 0 && (
                <p className="status">No alerts yet — run a pipeline script to generate some.</p>
            )}

            {!loading && !error && alerts.length > 0 && (
                <div className="table-wrap">
                    <table className="data-table">
                        <thead>
                            <tr>
                                <th className="num">ID</th>
                                <th>Type</th>
                                <th>Message</th>
                                <th className="num">Similarity</th>
                                <th>Created at</th>
                            </tr>
                        </thead>
                        <tbody>
                            {alerts.map((alert) => (
                                <tr key={alert.id}>
                                    <td className="num">{alert.id}</td>
                                    <td><span className={`badge badge-${alert.type}`}>{alert.type}</span></td>
                                    <td>{alert.message}</td>
                                    <td className="num">
                                        {alert.similarity != null ? alert.similarity.toFixed(3) : '—'}
                                    </td>
                                    <td className="nowrap">{new Date(alert.created_at).toLocaleString()}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    )
}

export default AlertsPage
