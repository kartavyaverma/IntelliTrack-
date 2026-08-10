import { useState, useEffect } from 'react'

const API_BASE = 'http://127.0.0.1:8000'

function HeatmapsPage() {
    const [heatmaps, setHeatmaps] = useState([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)

    useEffect(() => {
        fetch(`${API_BASE}/heatmaps`)
            .then((res) => {
                if (!res.ok) throw new Error(`API returned ${res.status}`)
                return res.json()
            })
            .then((data) => {
                setHeatmaps(data)
                setLoading(false)
            })
            .catch((err) => {
                setError(err.message)
                setLoading(false)
            })
    }, [])

    if (loading) return <div className="status">Loading heatmaps...</div>
    if (error) return <div className="status error">Failed to load heatmaps: {error}</div>

    if (heatmaps.length === 0) {
        return (
            <div className="status">
                No heatmaps found yet — run{' '}
                <code>python -m scripts.run_phase6_pipeline --heatmap</code> to generate some.
            </div>
        )
    }

    return (
        <div className="heatmap-grid">
            {heatmaps.map((hm) => (
                <div className="heatmap-card" key={hm.filename}>
                    <h3>{hm.filename.replace('_heatmap.jpg', '').replace('phase6_', '')}</h3>
                    <img src={`${API_BASE}${hm.url}`} alt={hm.filename} />
                </div>
            ))}
        </div>
    )
}

export default HeatmapsPage