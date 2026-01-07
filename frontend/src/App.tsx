import React from 'react'
import { Routes, Route, Link } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import Standings from './pages/Standings'
import Driver from './pages/Driver'
import LineupBuilder from './pages/LineupBuilder'
import LeagueAdmin from './pages/LeagueAdmin'
import Results from './pages/Results'

export default function App(){
  return (
    <div className="site">
      <header className="site-header">
        <div className="container">
          <h1><Link to="/">Fantasy NASCAR</Link></h1>
          <nav>
            <Link to="/">Dashboard</Link>
            <Link to="/lineup">Lineup Builder</Link>
            <Link to="/admin">League Admin</Link>
            <Link to="/standings">Standings</Link>
            <Link to="/results">Results</Link>
          </nav>
        </div>
      </header>
      <main className="container">
        <Routes>
          <Route path="/" element={<Dashboard/>} />
          <Route path="/lineup" element={<LineupBuilder/>} />
          <Route path="/admin" element={<LeagueAdmin/>} />
          <Route path="/standings" element={<Standings/>} />
          <Route path="/results" element={<Results/>} />
          <Route path="/driver/:id" element={<Driver/>} />
        </Routes>
      </main>
    </div>
  )
}
