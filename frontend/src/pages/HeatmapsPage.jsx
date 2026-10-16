import { useState, useEffect } from 'react'
import { API_BASE, getJSON, API_HINT } from '../api'

function HeatmapsPage() {
    const [heatmaps, setHeatmaps] = useState([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)

    useEffect(() => {
        getJSON('/heatmaps')
            .then(setHeatmaps)
            .catch((err) => setError(err.message))
            .finally(() => setLoading(false))
    }, [])

    if (loading) return <div className="status">Loading heatmaps...</div>
    if (error) {
        return (
            <div className="status error">
                <p>Failed to load heatmaps: {error}</p>
                <p>{API_HINT}</p>
            </div>
        )
    }

    if (heatmaps.length === 0) {
        return (
            <div className="status">
                No heatmaps found yet — run <code>python -m scripts.run_phase6_pipeline</code> to
                generate some.
            </div>
        )
    }

    return (
        <div className="heatmap-grid">
            {heatmaps.map((hm) => (
                <div className="card heatmap-card" key={hm.filename}>
                    <h3>{hm.filename.replace('_heatmap.jpg', '').replace('phase6_', '')}</h3>
                    {hm.updated_at && (
                        <p className="meta">Generated {new Date(hm.updated_at).toLocaleString()}</p>
                    )}
                    <img src={`${API_BASE}${hm.url}`} alt={`Heatmap for ${hm.filename}`} />
                </div>
            ))}
        </div>
    )
}

export default HeatmapsPage
