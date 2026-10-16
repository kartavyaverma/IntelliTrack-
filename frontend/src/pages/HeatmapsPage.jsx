import { useState, useEffect } from 'react'
import { API_BASE, getJSON, API_HINT } from '../api'
import { Status } from '../ui'

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

    if (loading) return <Status title="Loading heatmaps…" />
    if (error) return <Status kind="error" title={`Failed to load heatmaps: ${error}`}>{API_HINT}</Status>

    if (heatmaps.length === 0) {
        return (
            <Status title="No heatmaps yet">
                Run <code>python -m scripts.run_phase6_pipeline</code> to generate some.
            </Status>
        )
    }

    return (
        <div className="heatmap-grid">
            {heatmaps.map((hm) => {
                const camera = hm.filename.replace('_heatmap.jpg', '').replace('phase6_', '')
                return (
                    <div className="panel heatmap-card" key={hm.filename}>
                        <figure>
                            <img src={`${API_BASE}${hm.url}`} alt={`Heatmap for ${camera}`} />
                        </figure>
                        <div className="card-foot">
                            <span className="camera-tag">{camera}</span>
                            {hm.updated_at && (
                                <span className="card-meta mono">
                                    {new Date(hm.updated_at).toLocaleString()}
                                </span>
                            )}
                        </div>
                    </div>
                )
            })}
        </div>
    )
}

export default HeatmapsPage
