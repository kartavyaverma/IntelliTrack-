import { useState, useEffect } from 'react'

const API_BASE = 'http://127.0.0.1:8000'

function PeoplePage() {
    const [people, setPeople] = useState([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)

    const [name, setName] = useState('')
    const [file, setFile] = useState(null)
    const [uploading, setUploading] = useState(false)
    const [uploadError, setUploadError] = useState(null)
    const [uploadSuccess, setUploadSuccess] = useState(null)

    const loadPeople = () => {
        setLoading(true)
        fetch(`${API_BASE}/people`)
            .then((res) => res.json())
            .then((data) => {
                setPeople(data)
                setLoading(false)
            })
            .catch((err) => {
                setError(err.message)
                setLoading(false)
            })
    }

    useEffect(loadPeople, [])

    const handleUpload = async (e) => {
        e.preventDefault()
        setUploadError(null)
        setUploadSuccess(null)

        if (!name.trim() || !file) {
            setUploadError('Both a name and a photo file are required.')
            return
        }

        setUploading(true)
        const formData = new FormData()
        formData.append('name', name.trim())
        formData.append('file', file)

        try {
            const res = await fetch(`${API_BASE}/people`, {
                method: 'POST',
                body: formData,
            })
            const data = await res.json()

            if (!res.ok) {
                
                throw new Error(data.detail || `Upload failed (${res.status})`)
            }

            setUploadSuccess(`Registered '${data.name}' (face confidence: ${data.det_score.toFixed(3)})`)
            setName('')
            setFile(null)
            e.target.reset()
            loadPeople() 
        } catch (err) {
            setUploadError(err.message)
        } finally {
            setUploading(false)
        }
    }

    return (
        <div>
            <form className="upload-form" onSubmit={handleUpload}>
                <h3>Register a new reference person</h3>
                <div className="upload-fields">
                    <input
                        type="text"
                        placeholder="Person's name"
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                    />
                    <input
                        type="file"
                        accept="image/jpeg,image/png"
                        onChange={(e) => setFile(e.target.files[0])}
                    />
                    <button type="submit" disabled={uploading}>
                        {uploading ? 'Uploading...' : 'Register'}
                    </button>
                </div>
                {uploadError && <p className="upload-message error">{uploadError}</p>}
                {uploadSuccess && <p className="upload-message success">{uploadSuccess}</p>}
                <p className="upload-hint">
                    Note: this registers the person in the database. It does not update
                    a pipeline that's already running — restart the pipeline script to
                    pick up a new reference photo.
                </p>
            </form>

            <h3 style={{ marginTop: '2rem' }}>Registered people</h3>
            {loading && <div className="status">Loading...</div>}
            {error && <div className="status error">Failed to load people: {error}</div>}

            {!loading && !error && (
                <div className="people-grid">
                    {people.map((p) => (
                        <div className="person-card" key={p.id}>
                            <img src={`${API_BASE}${p.photo_url}`} alt={p.name} />
                            <p>{p.name}</p>
                        </div>
                    ))}
                    {people.length === 0 && (
                        <p className="status">No people registered yet — use the form above.</p>
                    )}
                </div>
            )}
        </div>
    )
}

export default PeoplePage