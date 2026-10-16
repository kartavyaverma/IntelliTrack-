import { useState, useEffect, useCallback } from 'react'
import { getJSON, API_HINT } from '../api'
import { Toolbar, TypeBadge, Similarity, Status } from '../ui'

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
            <Toolbar lastUpdated={lastUpdated} onRefresh={fetchSightings}>
                <label className="field">
                    Type
                    <select value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)}>
                        <option value="">All</option>
                        <option value="face">Face</option>
                        <option value="reid">Re-ID</option>
                    </select>
                </label>

                <label className="field">
                    Camera
                    <select value={cameraFilter} onChange={(e) => setCameraFilter(e.target.value)}>
                        <option value="">All</option>
                        {cameras.map((cam) => (
                            <option key={cam.id} value={cam.camera_id}>{cam.camera_id}</option>
                        ))}
                    </select>
                </label>

                <span className="count"><strong>{sightings.length}</strong> sighting(s)</span>
            </Toolbar>

            {loading && <Status title="Loading sightings…" />}
            {error && (
                <Status kind="error" title={`Failed to load sightings: ${error}`}>{API_HINT}</Status>
            )}

            {!loading && !error && sightings.length === 0 && (
                <Status title="No sightings match this filter" />
            )}

            {!loading && !error && sightings.length > 0 && (
                <div className="panel table-wrap">
                    <table className="data-table">
                        <thead>
                            <tr>
                                <th className="num">#</th>
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
                                    <td className="num id">{s.id}</td>
                                    <td><TypeBadge type={s.type} /></td>
                                    <td className="mono strong">{s.camera_id}</td>
                                    <td className="num">{s.track_id >= 0 ? s.track_id : '—'}</td>
                                    <td className="num">
                                        {s.timestamp_sec != null ? `${s.timestamp_sec.toFixed(2)}s` : '—'}
                                    </td>
                                    <td className="num"><Similarity value={s.similarity} type={s.type} /></td>
                                    <td className="strong">{describeMatch(s)}</td>
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
