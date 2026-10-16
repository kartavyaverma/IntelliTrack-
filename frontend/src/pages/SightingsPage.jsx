import { useState, useEffect, useCallback } from 'react'
import { getJSON, API_HINT } from '../api'

const POLL_INTERVAL_MS = 5000

// A face sighting matched a registered person; a reid sighting matched
// another camera's track. Show whichever applies in one column.
function describeMatch(s) {
    if (s.type === 'face') return s.person_name ?? (s.person_id != null ? `person #${s.person_id}` : '—')
    if (s.matched_camera_id) return `${s.matched_camera_id} · track ${s.matched_track_id}`
    return '—'
}

function SightingsPage() {
    const [sightings, setSightings] = useState([])
    const [cameras, setCameras] = useState([])
    const [typeFilter, setTypeFilter] = useState('')
    const [cameraFilter, setCameraFilter] = useState('')
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)
    const [lastUpdated, setLastUpdated] = useState(null)

    useEffect(() => {
        getJSON('/cameras').then(setCameras).catch(() => { })
    }, [])

    const fetchSightings = useCallback(() => {
        const params = new URLSearchParams({ limit: '200' })
        if (typeFilter) params.set('sighting_type', typeFilter)
        if (cameraFilter) params.set('camera_id', cameraFilter)

        return getJSON(`/sightings?${params}`)
            .then((data) => {
                setSightings(data)
                setError(null)
                setLastUpdated(new Date())
            })
            .catch((err) => setError(err.message))
            .finally(() => setLoading(false))
    }, [typeFilter, cameraFilter])

    useEffect(() => {
        setLoading(true)
        fetchSightings() // initial load whenever filters change
        const interval = setInterval(fetchSightings, POLL_INTERVAL_MS)
        return () => clearInterval(interval)
    }, [fetchSightings])

    return (
        <div>
            <div className="toolbar">
                <label>
                    Type
                    <select value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)}>
                        <option value="">All</option>
                        <option value="face">Face</option>
                        <option value="reid">Re-ID</option>
                    </select>
                </label>

                <label>
                    Camera
                    <select value={cameraFilter} onChange={(e) => setCameraFilter(e.target.value)}>
                        <option value="">All</option>
                        {cameras.map((cam) => (
                            <option key={cam.id} value={cam.camera_id}>{cam.camera_id}</option>
                        ))}
                    </select>
                </label>

                <span className="count">{sightings.length} sighting(s)</span>
                <span className="spacer" />
                {lastUpdated && (
                    <span className="last-updated">Updated {lastUpdated.toLocaleTimeString()}</span>
                )}
                <button className="btn" onClick={fetchSightings}>Refresh</button>
            </div>

            {loading && <div className="status">Loading sightings...</div>}
            {error && (
                <div className="status error">
                    <p>Failed to load sightings: {error}</p>
                    <p>{API_HINT}</p>
                </div>
            )}

            {!loading && !error && sightings.length === 0 && (
                <p className="status">No sightings match this filter.</p>
            )}

            {!loading && !error && sightings.length > 0 && (
                <div className="table-wrap">
                    <table className="data-table">
                        <thead>
                            <tr>
                                <th className="num">ID</th>
                                <th>Type</th>
                                <th>Camera</th>
                                <th className="num">Track</th>
                                <th className="num">Video time</th>
                                <th className="num">Similarity</th>
                                <th>Matched</th>
                            </tr>
                        </thead>
                        <tbody>
                            {sightings.map((s) => (
                                <tr key={s.id}>
                                    <td className="num">{s.id}</td>
                                    <td><span className={`badge badge-${s.type}`}>{s.type}</span></td>
                                    <td>{s.camera_id}</td>
                                    <td className="num">{s.track_id >= 0 ? s.track_id : '—'}</td>
                                    <td className="num">
                                        {s.timestamp_sec != null ? `${s.timestamp_sec.toFixed(2)}s` : '—'}
                                    </td>
                                    <td className="num">{s.similarity != null ? s.similarity.toFixed(3) : '—'}</td>
                                    <td>{describeMatch(s)}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    )
}

export default SightingsPage
