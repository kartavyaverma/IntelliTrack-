// Small presentational pieces shared by the pages.

const ICON_PATHS = {
  alerts: 'M18 8a6 6 0 1 0-12 0c0 7-3 9-3 9h18s-3-2-3-9M13.73 21a2 2 0 0 1-3.46 0',
  sightings: 'M1 12s4-8 11-8 11 8 11 8-4 8-11 8S1 12 1 12zM12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6z',
  heatmaps: 'M3 3h7v7H3zM14 3h7v7h-7zM14 14h7v7h-7zM3 14h7v7H3z',
  people:
    'M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75',
  refresh: 'M23 4v6h-6M1 20v-6h6M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15',
  upload: 'M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12',
}

export function Icon({ name, size = 18 }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d={ICON_PATHS[name]} />
    </svg>
  )
}

export function TypeBadge({ type }) {
  return <span className={`badge badge-${type}`}>{type === 'reid' ? 'Re-ID' : type}</span>
}

// Similarity is a cosine score in [0, 1]; the bar makes it scannable.
export function Similarity({ value, type }) {
  if (value == null) return <span className="muted">—</span>
  const pct = Math.max(0, Math.min(1, value)) * 100
  return (
    <span className="similarity">
      <span className="mono">{value.toFixed(3)}</span>
      <span className="meter" aria-hidden="true">
        <span className={`meter-fill meter-${type}`} style={{ width: `${pct}%` }} />
      </span>
    </span>
  )
}

export function Toolbar({ children, lastUpdated, onRefresh }) {
  return (
    <div className="toolbar">
      {children}
      <span className="spacer" />
      {lastUpdated && (
        <span className="last-updated">
          <span className="live-dot" aria-hidden="true" />
          Updated <span className="mono">{lastUpdated.toLocaleTimeString()}</span>
        </span>
      )}
      {onRefresh && (
        <button className="btn btn-ghost" onClick={onRefresh}>
          <Icon name="refresh" size={15} />
          Refresh
        </button>
      )}
    </div>
  )
}

export function Status({ kind = 'info', title, children }) {
  return (
    <div className={`status status-${kind}`}>
      {title && <p className="status-title">{title}</p>}
      {children && <div className="status-body">{children}</div>}
    </div>
  )
}
