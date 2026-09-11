import { NavLink, Route, Routes } from 'react-router-dom'
import { ArchitecturePage } from './pages/ArchitecturePage'
import { CsvPage } from './pages/CsvPage'
import { DashboardPage } from './pages/DashboardPage'
import { DemoPage } from './pages/DemoPage'
import { MissionPage } from './pages/MissionPage'
import { ReplayPage } from './pages/ReplayPage'
import { ValidationPage } from './pages/ValidationPage'
import { SettingsPage } from './pages/SettingsPage'
import { TelemetryProvider } from './context/TelemetryContext'

// Sidebar SVG icons (inline, no external dep)
function IconDashboard() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      <rect x="3" y="3" width="7" height="7" rx="1"/>
      <rect x="14" y="3" width="7" height="7" rx="1"/>
      <rect x="3" y="14" width="7" height="7" rx="1"/>
      <rect x="14" y="14" width="7" height="7" rx="1"/>
    </svg>
  )
}
function IconDemo() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
    </svg>
  )
}
function IconMission() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      <path d="M12 2L2 7l10 5 10-5-10-5z"/>
      <path d="M2 17l10 5 10-5"/>
      <path d="M2 12l10 5 10-5"/>
    </svg>
  )
}
function IconDiag() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      <circle cx="12" cy="12" r="10"/>
      <path d="M12 8v4l3 3"/>
    </svg>
  )
}
function IconAnalytics() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
    </svg>
  )
}
function IconHistory() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      <polyline points="17 1 21 5 17 9"/>
      <path d="M3 11V9a4 4 0 0 1 4-4h14"/>
      <polyline points="7 23 3 19 7 15"/>
      <path d="M21 13v2a4 4 0 0 1-4 4H3"/>
    </svg>
  )
}
function IconReports() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
      <polyline points="14 2 14 8 20 8"/>
      <line x1="16" y1="13" x2="8" y2="13"/>
      <line x1="16" y1="17" x2="8" y2="17"/>
      <polyline points="10 9 9 9 8 9"/>
    </svg>
  )
}
function IconSettings() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      <circle cx="12" cy="12" r="3"/>
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>
    </svg>
  )
}

const navItems = [
  { to: '/', label: 'Dashboard', icon: <IconDashboard />, end: true },
  { to: '/demo', label: 'Live Demo', icon: <IconDemo /> },
  { to: '/mission', label: 'Mission', icon: <IconMission /> },
  { to: '/replay', label: 'Analytics', icon: <IconAnalytics /> },
  { to: '/csv', label: 'CSV', icon: <IconHistory /> },
  { to: '/validation', label: 'Validate', icon: <IconReports /> },
  { to: '/architecture', label: 'Arch', icon: <IconDiag /> },
]

export default function App() {
  return (
    <TelemetryProvider>
      <div className="app-root">
        {/* Sidebar */}
        <aside className="sidebar">
          <div style={{ padding: '6px 0 8px', width: '100%', display: 'flex', justifyContent: 'center' }}>
            <div style={{
              width: 34, height: 34, borderRadius: 8,
              background: 'linear-gradient(135deg, #ea6a0a 0%, #f97316 100%)',
              display: 'flex', alignItems: 'center', justifyContent: 'center'
            }}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
                <path d="M12 2L4 7v10l8 5 8-5V7L12 2z" fill="white" opacity="0.9"/>
                <path d="M12 2l8 5-8 5-8-5 8-5z" fill="white"/>
              </svg>
            </div>
          </div>

          <div className="sidebar-divider" />

          {navItems.map(item => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) => `sidebar-item${isActive ? ' active' : ''}`}
              title={item.label}
            >
              {item.icon}
              <span className="sidebar-item-label">{item.label}</span>
            </NavLink>
          ))}

          <div className="sidebar-spacer" />
          <div className="sidebar-divider" />

          <NavLink
            to="/settings"
            className={({ isActive }) => `sidebar-item${isActive ? ' active' : ''}`}
            title="Settings"
          >
            <IconSettings />
            <span className="sidebar-item-label">Settings</span>
          </NavLink>

          <div className="sidebar-footer">
            <div className="sidebar-footer-text">SAFE SKIES<br/>SMARTER<br/>ENGINES</div>
          </div>
        </aside>

        {/* Main content */}
        <div className="main-content">
          <Routes>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/demo" element={<DemoPage />} />
            <Route path="/mission" element={<MissionPage />} />
            <Route path="/replay" element={<ReplayPage />} />
            <Route path="/csv" element={<CsvPage />} />
            <Route path="/validation" element={<ValidationPage />} />
            <Route path="/architecture" element={<ArchitecturePage />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Routes>
        </div>
      </div>
    </TelemetryProvider>
  )
}
