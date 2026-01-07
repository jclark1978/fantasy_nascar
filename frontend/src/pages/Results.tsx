import React, {useEffect, useState} from 'react'
import {fetchResults} from '../api'

export default function Results(){
  const [year, setYear] = useState(new Date().getFullYear())
  const [results, setResults] = useState<any[]>([])
  const [error, setError] = useState('')

  useEffect(()=>{
    setError('')
    fetchResults(year, 1)
      .then((data:any)=>setResults(Array.isArray(data) ? data : []))
      .catch((err:any)=>setError(err.message || 'Unable to load results'))
  },[year])

  return (
    <div className="page">
      <section className="panel hero">
        <div>
          <h2>Race Results</h2>
          <p>Official Cup Series results by race.</p>
        </div>
        <div className="inline">
          <label>Season</label>
          <input type="number" value={year} onChange={e=>setYear(Number(e.target.value))} />
        </div>
      </section>

      {error && <div className="error">{error}</div>}

      <section className="panel">
        <div className="race-grid">
          {results.map((race:any) => (
            <div key={race.raceId || race.name} className="race-card">
              <div className="race-name">{race.name || 'Race'}</div>
              <div className="race-meta">{race.track || 'Track TBA'}</div>
              <div className="race-meta">{race.date ? race.date.slice(0,10) : 'Date TBA'}</div>
              <div className="race-meta">Winner: {race.winner || 'TBA'}</div>
              {race.poleWinner && <div className="race-meta">Pole: {race.poleWinner}</div>}
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}
