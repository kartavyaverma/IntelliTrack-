import { useState } from 'react'
import './App.css'
import AlertsPage from './pages/AlertsPage'
import SightingsPage from './pages/SightingsPage'
import HeatmapsPage from './pages/HeatmapsPage'
import PeoplePage from './pages/PeoplePage'

function App() {
  const [activeTab, setActiveTab] = useState('alerts')

  return (
    <div className="app">
      <h1>IntelliTrack Dashboard</h1>

      <nav className="tabs">
        <button
          className={activeTab === 'alerts' ? 'tab active' : 'tab'}
          onClick={() => setActiveTab('alerts')}
        >
          Alerts
        </button>
        <button
          className={activeTab === 'sightings' ? 'tab active' : 'tab'}
          onClick={() => setActiveTab('sightings')}
        >
          Sightings
        </button>
        <button
          className={activeTab === 'heatmaps' ? 'tab active' : 'tab'}
          onClick={() => setActiveTab('heatmaps')}
        >
          Heatmaps
        </button>
        <button
          className={activeTab === 'people' ? 'tab active' : 'tab'}
          onClick={() => setActiveTab('people')}
        >
          People
        </button>
      </nav>

      {activeTab === 'alerts' && <AlertsPage />}
      {activeTab === 'sightings' && <SightingsPage />}
      {activeTab === 'heatmaps' && <HeatmapsPage />}
      {activeTab === 'people' && <PeoplePage />}
    </div>
  )
}

export default App