import { useState, useEffect } from 'react'

const API_BASE = 'http://127.0.0.1:8000'

function SightingsPage() {
    const [sightings, setSightings] = useState([])
    const [cameras, setCameras] = useState([])
    const [typeFilter, setTypeFilter] = useState('')
    const [cameraFilter, setCameraFilter] = useState('')
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)

    
    useEffect(() => {
        fetch(`${API_BASE}/cameras`)
            .then((res) => res.json())
            .then(setCameras)
            .catch(() => { }) 
    }, [])

    
    useEffect(() => {
        setLoading(true)
        const params = new URLSearchParams({ limit: '200' })
        if (typeFilter) params.set('sighting_type', typeFilter)
        if (cameraFilter) params.set('camera_id', cameraFilter)

        fetch(`${API_BASE}/sightings?${params}`)
            .then((res) => {
                if (!res.ok) throw new Error(`API returned ${res.status}`)
                return res.json()
            })
            .then((data) => {
                setSightings(data)
                setLoading(false)
            })
            .catch((err) => {
                setError(err.message)
                setLoading(false)
            })
    }, [typeFilter, cameraFilter])

    return (
        <div>
            <div className="filters">
                <label>
                    Type:
                    <select value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)}>
                        <option value="">All</option>
                        <option value="face">Face</option>
                        <option value="reid">Re-ID</option>
                    </select>
                </label>

                <label>
                    Camera:
                    <select value={cameraFilter} onChange={(e) => setCameraFilter(e.target.value)}>
                        <option value="">All</option>
                        {cameras.map((cam) => (
                            <option key={cam.id} value={cam.camera_id}>{cam.camera_id}</option>
                        ))}
                    </select>
                </label>
            </div>

            {loading && <div className="status">Loading sightings...</div>}
            {error && <div className="status error">Failed to load sightings: {error}</div>}

            {!loading && !error && (
                <>
                    <p className="subtitle">{sightings.length} sighting(s)</p>
                    <table className="data-table">
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>Type</th>
                                <th>Camera</th>
                                <th>Track ID</th>
                                <th>Timestamp</th>
                                <th>Similarity</th>
                                <th>Matched Camera</th>
                                <th>Matched Track</th>
                            </tr>
                        </thead>
                        <tbody>
                            {sightings.map((s) => (
                                <tr key={s.id}>
                                    <td>{s.id}</td>
                                    <td><span className={`badge badge-${s.type}`}>{s.type}</span></td>
                                    <td>{s.camera_id}</td>
                                    <td>{s.track_id}</td>
                                    <td>{s.timestamp_sec != null ? `${s.timestamp_sec.toFixed(2)}s` : '—'}</td>
                                    <td>{s.similarity != null ? s.similarity.toFixed(3) : '—'}</td>
                                    <td>{s.matched_camera_id ?? '—'}</td>
                                    <td>{s.matched_track_id ?? '—'}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                    {sightings.length === 0 && (
                        <p className="status">No sightings match this filter.</p>
                    )}
                </>
            )}
        </div>
    )
}

export default SightingsPage