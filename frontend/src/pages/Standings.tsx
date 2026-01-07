import React, {useEffect, useMemo, useState} from 'react'
import {fetchStandings} from '../api'

export default function Standings(){
  const [year, setYear] = useState(new Date().getFullYear())
  const [standings, setStandings] = useState<any[]>([])
  const [error, setError] = useState('')

  useEffect(()=>{
    setError('')
    fetchStandings(year, 1)
      .then((data:any)=>setStandings(data?.standings?.entries || []))
      .catch((err:any)=>setError(err.message || 'Unable to load standings'))
  },[year])

  const rows = useMemo(()=>{
    return standings.map((entry:any) => {
      const athlete = entry.athlete || {}
      const stats = entry.stats || []
      const find = (name:string) => stats.find((stat:any)=>stat.name === name)
      return {
        id: athlete.id,
        name: athlete.displayName || athlete.fullName || athlete.name,
        rank: find('rank')?.displayValue || find('rank')?.value,
        points: find('championshipPts')?.displayValue || find('championshipPts')?.value,
        wins: find('wins')?.displayValue || find('wins')?.value,
        top5: find('top5')?.displayValue || find('top5')?.value,
        top10: find('top10')?.displayValue || find('top10')?.value,
      }
    })
  },[standings])

  return (
    <div className="page">
      <section className="panel hero">
        <div>
          <h2>Season Standings</h2>
          <p>Cup Series standings and race results for the current season.</p>
        </div>
        <div className="inline">
          <label>Season</label>
          <input type="number" value={year} onChange={e=>setYear(Number(e.target.value))} />
        </div>
      </section>

      {error && <div className="error">{error}</div>}

      <section className="panel">
        <h3>Driver Standings</h3>
        <div className="table">
          <div className="row header">
            <div>Rank</div>
            <div>Driver</div>
            <div>Points</div>
            <div>Wins</div>
            <div>Top 5</div>
            <div>Top 10</div>
          </div>
          {rows.map((row:any) => (
            <div className="row" key={row.id || row.name}>
              <div>{row.rank}</div>
              <div>{row.name}</div>
              <div>{row.points}</div>
              <div>{row.wins}</div>
              <div>{row.top5}</div>
              <div>{row.top10}</div>
            </div>
          ))}
        </div>
      </section>

    </div>
  )
}
