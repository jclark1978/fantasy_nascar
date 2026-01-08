import React, {useEffect, useMemo, useState} from 'react'
import {guestLogin, registerUser, loginUser, fetchLeagues, updateLeagueSettings} from '../api'

type LeagueMembership = {league:{id:number,name:string,code:string,settings:any}, role:string}

export default function LeagueAdmin(){
  const [token, setToken] = useState<string | null>(localStorage.getItem('token'))
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [authError, setAuthError] = useState('')
  const [leagues, setLeagues] = useState<LeagueMembership[]>([])
  const [leagueId, setLeagueId] = useState<number | null>(null)
  const [settings, setSettings] = useState<any | null>(null)
  const [status, setStatus] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(()=>{
    if(!token){
      setLeagues([])
      setLeagueId(null)
      return
    }
    fetchLeagues(token).then(setLeagues).catch(()=>setLeagues([]))
  },[token])

  useEffect(()=>{
    if(!leagueId) return
    const league = leagues.find(l => l.league.id === leagueId)
    if(league?.league?.settings){
      setSettings({...league.league.settings})
    }else{
      setSettings(null)
    }
  },[leagueId, leagues])

  const selected = useMemo(()=>leagues.find(l => l.league.id === leagueId) || null, [leagues, leagueId])

  async function handleGuest(){
    setAuthError('')
    const t = await guestLogin()
    localStorage.setItem('token', t.access_token)
    setToken(t.access_token)
  }

  async function handleRegister(){
    setAuthError('')
    try{
      const t = await registerUser(email, password)
      localStorage.setItem('token', t.access_token)
      setToken(t.access_token)
    }catch(err:any){
      setAuthError(err.message || 'Registration failed')
    }
  }

  async function handleLogin(){
    setAuthError('')
    try{
      const t = await loginUser(email, password)
      localStorage.setItem('token', t.access_token)
      setToken(t.access_token)
    }catch(err:any){
      setAuthError(err.message || 'Login failed')
    }
  }

  function handleLogout(){
    localStorage.removeItem('token')
    setToken(null)
  }

  async function saveSettings(){
    if(!token || !leagueId || !settings) return
    setBusy(true)
    setError('')
    setStatus('')
    try{
      const payload = {
        top_pick_count: Number(settings.top_pick_count),
        middle_pick_count: Number(settings.middle_pick_count),
        bottom_pick_count: Number(settings.bottom_pick_count),
        top_rank_max: Number(settings.top_rank_max),
        middle_rank_max: Number(settings.middle_rank_max),
        max_starts_per_driver: Number(settings.max_starts_per_driver),
        lock_hours: Number(settings.lock_hours),
      }
      await updateLeagueSettings(token, leagueId, payload)
      setStatus('Settings saved.')
    }catch(err:any){
      setError(err.message || 'Unable to save settings')
    }finally{
      setBusy(false)
    }
  }

  return (
    <div className="page">
      <section className="panel hero">
        <div>
          <h2>League Admin</h2>
          <p>Commissioners can tune lineup rules for their league.</p>
        </div>
        <div className="auth-panel">
          {token ? (
            <button className="ghost" onClick={handleLogout}>Log out</button>
          ) : (
            <>
              <input placeholder="Email" value={email} onChange={e=>setEmail(e.target.value)} />
              <input placeholder="Password" type="password" value={password} onChange={e=>setPassword(e.target.value)} />
              <div className="auth-actions">
                <button onClick={handleRegister}>Sign up</button>
                <button onClick={handleLogin}>Log in</button>
                <button className="ghost" onClick={handleGuest}>Guest</button>
              </div>
            </>
          )}
          {authError && <div className="error">{authError}</div>}
        </div>
      </section>

      <section className="panel">
        <div className="inline">
          <label>League</label>
          <select value={leagueId ?? ''} onChange={e=>setLeagueId(e.target.value ? Number(e.target.value) : null)}>
            <option value="" disabled>Select a league</option>
            {leagues.map(m => (
              <option key={m.league.id} value={m.league.id}>
                {m.league.name} ({m.league.code})
              </option>
            ))}
          </select>
        </div>
        {selected && selected.role !== 'commissioner' && (
          <div className="notice">Only the league commissioner can edit settings.</div>
        )}
      </section>

      {selected && selected.role === 'commissioner' && settings && (
        <section className="panel">
          <h3>Lineup Rules</h3>
          <div className="grid three">
            <div>
              <label>Group A picks</label>
              <input type="number" min="0" value={settings.top_pick_count} onChange={e=>setSettings({...settings, top_pick_count: e.target.value})} />
            </div>
            <div>
              <label>Group B picks</label>
              <input type="number" min="0" value={settings.middle_pick_count} onChange={e=>setSettings({...settings, middle_pick_count: e.target.value})} />
            </div>
            <div>
              <label>Group C picks</label>
              <input type="number" min="0" value={settings.bottom_pick_count} onChange={e=>setSettings({...settings, bottom_pick_count: e.target.value})} />
            </div>
          </div>
          <div className="grid three">
            <div>
              <label>Top tier max rank</label>
              <input type="number" min="1" value={settings.top_rank_max} onChange={e=>setSettings({...settings, top_rank_max: e.target.value})} />
            </div>
            <div>
              <label>Middle tier max rank</label>
              <input type="number" min="1" value={settings.middle_rank_max} onChange={e=>setSettings({...settings, middle_rank_max: e.target.value})} />
            </div>
            <div>
              <label>Max starts per driver</label>
              <input type="number" min="1" value={settings.max_starts_per_driver} onChange={e=>setSettings({...settings, max_starts_per_driver: e.target.value})} />
            </div>
          </div>
          <div className="grid two">
            <div>
              <label>Lock hours before race</label>
              <input type="number" min="1" value={settings.lock_hours} onChange={e=>setSettings({...settings, lock_hours: e.target.value})} />
            </div>
            <div className="inline end">
              <button disabled={busy} onClick={saveSettings}>Save Settings</button>
            </div>
          </div>
          {status && <div className="success">{status}</div>}
          {error && <div className="error">{error}</div>}
        </section>
      )}
    </div>
  )
}
