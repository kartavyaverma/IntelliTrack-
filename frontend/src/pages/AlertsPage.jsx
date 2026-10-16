import { useState, useEffect, useCallback } from 'react'
import { getJSON, API_HINT } from '../api'
import { Toolbar, TypeBadge, Similarity, Status } from '../ui'

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
            <Toolbar lastUpdated={lastUpdated} onRefresh={fetchAlerts}>
                <span className="count"><strong>{alerts.length}</strong> alert(s)</span>
            </Toolbar>

            {loading && <Status title="Loading alerts…" />}
            {error && (
                <Status kind="error" title={`Failed to load alerts: ${error}`}>{API_HINT}</Status>
            )}

            {!loading && !error && alerts.length === 0 && (
                <Status title="No alerts yet">Run a pipeline script to generate some.</Status>
            )}

            {!loading && !error && alerts.length > 0 && (
                <div className="panel table-wrap">
                    <table className="data-table">
                        <thead>
                            <tr>
                                <th className="num">#</th>
                                <th>Type</th>
                                <th>Message</th>
                                <th className="num">Similarity</th>
                                <th>Raised at</th>
                            </tr>
                        </thead>
                        <tbody>
                            {alerts.map((alert) => (
                                <tr key={alert.id}>
                                    <td className="num id">{alert.id}</td>
                                    <td><TypeBadge type={alert.type} /></td>
                                    <td className="strong">{alert.message}</td>
                                    <td className="num"><Similarity value={alert.similarity} type={alert.type} /></td>
                                    <td className="nowrap mono muted">{new Date(alert.created_at).toLocaleString()}</td>
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
