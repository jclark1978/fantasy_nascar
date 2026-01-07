import React, {useEffect, useState} from 'react'
import {Link} from 'react-router-dom'
import {fetchRaces} from '../api'

export default function Dashboard(){
  const [races, setRaces] = useState<any[]>([])

  useEffect(()=>{ fetchRaces().then((r:any)=>setRaces(r)).catch(()=>setRaces([])) },[])

  return (
    <div className="page">
      <section className="panel hero">
        <div>
          <h2>Race Week Hub</h2>
          <p>Build your lineup, track standings, and keep the league racing.</p>
          <div className="inline">
            <Link className="button" to="/lineup">Build Lineup</Link>
            <Link className="button ghost" to="/admin">League Settings</Link>
          </div>
        </div>
        <div className="callout">
          <div className="label">Next Up</div>
          {races.length ? (
            <div>
              <div className="race-name">{races[0].name}</div>
              <div className="race-meta">{races[0].date ? races[0].date.slice(0,10) : 'Date TBA'}</div>
            </div>
          ) : (
            <div>Race schedule loading...</div>
          )}
        </div>
      </section>

      <section className="panel">
        <h3>Upcoming Races</h3>
        <div className="race-grid">
          {races.map(r => (
            <div key={r.raceId} className="race-card">
              <div className="race-name">{r.name}</div>
              <div className="race-meta">{r.date ? r.date.slice(0,10) : 'Date TBA'}</div>
              <div className="race-meta">Race ID {r.raceId}</div>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}
