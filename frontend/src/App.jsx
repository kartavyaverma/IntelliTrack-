import { useState } from 'react'
import './App.css'
import AlertsPage from './pages/AlertsPage'
import SightingsPage from './pages/SightingsPage'
import HeatmapsPage from './pages/HeatmapsPage'
import PeoplePage from './pages/PeoplePage'
import { Icon } from './ui'

const TABS = [
  {
    id: 'alerts',
    label: 'Alerts',
    Page: AlertsPage,
    title: 'Alerts',
    blurb: 'Matches that cleared the confidence floor and the per-camera cooldown.',
  },
  {
    id: 'sightings',
    label: 'Sightings',
    Page: SightingsPage,
    title: 'Sightings',
    blurb: 'Every raw face and cross-camera Re-ID match logged by the pipeline.',
  },
  {
    id: 'heatmaps',
    label: 'Heatmaps',
    Page: HeatmapsPage,
    title: 'Crowd heatmaps',
    blurb: 'Where people walked and stood, per camera, at the end of the last run.',
  },
  {
    id: 'people',
    label: 'People',
    Page: PeoplePage,
    title: 'Registered people',
    blurb: 'Reference photos the pipeline searches for in every frame.',
  },
]

function App() {
  const [activeTab, setActiveTab] = useState('alerts')
  const tab = TABS.find((t) => t.id === activeTab)
  const { Page } = tab

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <img src="/favicon.svg" alt="" width="30" height="30" />
          <div>
            <p className="brand-name">IntelliTrack</p>
            <p className="brand-sub">Surveillance console</p>
          </div>
        </div>

        <nav className="nav" aria-label="Sections">
          {TABS.map((t) => (
            <button
              key={t.id}
              className={t.id === activeTab ? 'nav-item active' : 'nav-item'}
              aria-current={t.id === activeTab ? 'page' : undefined}
              aria-label={t.label}
              onClick={() => setActiveTab(t.id)}
            >
              <Icon name={t.id} />
              <span>{t.label}</span>
            </button>
          ))}
        </nav>

        <p className="sidebar-foot">
          Tracking · Re-ID · Face match · Crowd analytics
        </p>
      </aside>

      <main className="content">
        <header className="page-head">
          <p className="eyebrow">{tab.label}</p>
          <h1>{tab.title}</h1>
          <p className="blurb">{tab.blurb}</p>
        </header>
        <Page />
      </main>
    </div>
  )
}

export default App
