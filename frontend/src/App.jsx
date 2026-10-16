import { useState } from 'react'
import './App.css'
import AlertsPage from './pages/AlertsPage'
import SightingsPage from './pages/SightingsPage'
import HeatmapsPage from './pages/HeatmapsPage'
import PeoplePage from './pages/PeoplePage'

const TABS = [
  { id: 'alerts', label: 'Alerts', Page: AlertsPage },
  { id: 'sightings', label: 'Sightings', Page: SightingsPage },
  { id: 'heatmaps', label: 'Heatmaps', Page: HeatmapsPage },
  { id: 'people', label: 'People', Page: PeoplePage },
]

function App() {
  const [activeTab, setActiveTab] = useState('alerts')
  const { Page } = TABS.find((t) => t.id === activeTab)

  return (
    <div className="app">
      <header className="app-header">
        <h1>IntelliTrack Dashboard</h1>
        <p className="tagline">
          Cross-camera tracking, missing-person face matching and crowd analytics
        </p>
      </header>

      <nav className="tabs" role="tablist">
        {TABS.map((t) => (
          <button
            key={t.id}
            role="tab"
            aria-selected={activeTab === t.id}
            className={activeTab === t.id ? 'tab active' : 'tab'}
            onClick={() => setActiveTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </nav>

      <main>
        <Page />
      </main>
    </div>
  )
}

export default App
