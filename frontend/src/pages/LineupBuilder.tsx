import React, {useEffect, useMemo, useState} from 'react'
import {
  fetchRaces,
  guestLogin,
  registerUser,
  loginUser,
  fetchLeagues,
  createLeague,
  joinLeague,
  fetchEligibility,
  saveLineup,
  updateLeagueSettings,
  fetchDriverProfile,
} from '../api'

type LeagueMembership = {league:{id:number,name:string,code:string,settings:any}, role:string}
type Race = {raceId:string, name:string, date?:string}
type Driver = {driver_id:string, name?:string, rank?:number, used:number, remaining:number}

const emptySelection = {top: [] as string[], middle: [] as string[], bottom: [] as string[]}
const formatDriverName = (value?:string) => {
  if(!value) return ''
  if(value.includes(' ')) return value
  return value.replace(/([a-z])([A-Z])/g, '$1 $2')
}
const slugifyName = (value?:string) => {
  if(!value) return ''
  return value
    .toLowerCase()
    .replace(/&/g, 'and')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/-+/g, '-')
    .replace(/(^-|-$)/g, '')
}

export default function LineupBuilder(){
  const [token, setToken] = useState<string | null>(localStorage.getItem('token'))
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [authError, setAuthError] = useState('')
  const [leagues, setLeagues] = useState<LeagueMembership[]>([])
  const [leagueId, setLeagueId] = useState<number | null>(null)
  const [leagueCode, setLeagueCode] = useState('')
  const [leagueName, setLeagueName] = useState('')
  const [races, setRaces] = useState<Race[]>([])
  const [raceId, setRaceId] = useState('')
  const [eligibility, setEligibility] = useState<any | null>(null)
  const [selection, setSelection] = useState({...emptySelection})
  const [status, setStatus] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [settingsDraft, setSettingsDraft] = useState<any | null>(null)
  const [detailOpen, setDetailOpen] = useState(false)
  const [detailLoading, setDetailLoading] = useState(false)
  const [detailError, setDetailError] = useState('')
  const [detailDriver, setDetailDriver] = useState<Driver | null>(null)
  const [detailProfile, setDetailProfile] = useState<any | null>(null)

  useEffect(()=>{
    fetchRaces().then((data:any)=>setRaces(Array.isArray(data)? data : [])).catch(()=>setRaces([]))
  },[])

  useEffect(()=>{
    if(!token){
      setLeagues([])
      setLeagueId(null)
      return
    }
    fetchLeagues(token).then(setLeagues).catch(()=>setLeagues([]))
  },[token])

  useEffect(()=>{
    if(leagueId && leagues.length){
      const match = leagues.find(l => l.league.id === leagueId)
      if(!match){
        setLeagueId(null)
      }
    }
  },[leagueId, leagues])

  const selectedLeague = useMemo(()=>leagues.find(l => l.league.id === leagueId) || null, [leagues, leagueId])
  const selectedRace = useMemo(()=>races.find(r => String(r.raceId) === String(raceId)) || null, [races, raceId])

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
    setEligibility(null)
    setSelection({...emptySelection})
  }

  async function handleCreateLeague(){
    if(!token || !leagueName.trim()) return
    setBusy(true)
    setError('')
    try{
      await createLeague(token, {name: leagueName.trim()})
      setLeagueName('')
      const updated = await fetchLeagues(token)
      setLeagues(updated)
    }catch(err:any){
      setError(err.message || 'Unable to create league')
    }finally{
      setBusy(false)
    }
  }

  async function handleJoinLeague(){
    if(!token || !leagueCode.trim()) return
    setBusy(true)
    setError('')
    try{
      await joinLeague(token, {code: leagueCode.trim()})
      setLeagueCode('')
      const updated = await fetchLeagues(token)
      setLeagues(updated)
    }catch(err:any){
      setError(err.message || 'Unable to join league')
    }finally{
      setBusy(false)
    }
  }

  function isSelected(driverId:string){
    return selection.top.includes(driverId) || selection.middle.includes(driverId) || selection.bottom.includes(driverId)
  }

  function toggleDriver(tier:'top'|'middle'|'bottom', driverId:string){
    setSelection(prev => {
      const current = prev[tier]
      const alreadySelected = prev.top.includes(driverId) || prev.middle.includes(driverId) || prev.bottom.includes(driverId)
      if(current.includes(driverId)){
        return {...prev, [tier]: current.filter(id => id !== driverId)}
      }
      if(alreadySelected) return prev
      const max = eligibility?.tiers?.[tier]?.max_picks || 0
      if(current.length >= max) return prev
      return {...prev, [tier]: [...current, driverId]}
    })
  }

  async function loadEligibility(){
    if(!token || !leagueId || !raceId) return
    setBusy(true)
    setError('')
    try{
      const year = selectedRace?.date ? new Date(selectedRace.date).getUTCFullYear() : undefined
      const data = await fetchEligibility(token, {league_id: leagueId, race_id: raceId, year})
      setEligibility(data)
      if(data.current_lineup?.entries){
        const next = {...emptySelection}
        for(const entry of data.current_lineup.entries){
          if(next[entry.tier]){
            next[entry.tier].push(entry.driver_id)
          }
        }
        setSelection(next)
      }else{
        setSelection({...emptySelection})
      }
    }catch(err:any){
      setError(err.message || 'Unable to load eligibility')
    }finally{
      setBusy(false)
    }
  }

  useEffect(()=>{
    if(selectedLeague?.role === 'commissioner' && selectedLeague.league?.settings){
      setSettingsDraft({...selectedLeague.league.settings})
    }else{
      setSettingsDraft(null)
    }
  },[selectedLeague])

  async function saveSettings(){
    if(!token || !leagueId || !settingsDraft) return
    setBusy(true)
    setError('')
    setStatus('')
    try{
      const payload = {
        top_pick_count: Number(settingsDraft.top_pick_count),
        middle_pick_count: Number(settingsDraft.middle_pick_count),
        bottom_pick_count: Number(settingsDraft.bottom_pick_count),
        top_rank_max: Number(settingsDraft.top_rank_max),
        middle_rank_max: Number(settingsDraft.middle_rank_max),
        max_starts_per_driver: Number(settingsDraft.max_starts_per_driver),
        lock_hours: Number(settingsDraft.lock_hours),
      }
      await updateLeagueSettings(token, leagueId, payload)
      setStatus('Settings saved.')
      const updated = await fetchLeagues(token)
      setLeagues(updated)
    }catch(err:any){
      setError(err.message || 'Unable to save settings')
    }finally{
      setBusy(false)
    }
  }

  async function submitLineup(){
    if(!token || !leagueId || !raceId || !eligibility) return
    setBusy(true)
    setStatus('')
    setError('')
    try{
      const entries = [
        ...selection.top.map(driver_id => ({driver_id, tier:'top'})),
        ...selection.middle.map(driver_id => ({driver_id, tier:'middle'})),
        ...selection.bottom.map(driver_id => ({driver_id, tier:'bottom'})),
      ]
      const season_year = eligibility.season_year
      await saveLineup(token, {league_id: leagueId, race_id: raceId, season_year, entries})
      setStatus('Lineup saved.')
    }catch(err:any){
      setError(err.message || 'Unable to save lineup')
    }finally{
      setBusy(false)
    }
  }

  async function openDriverDetails(driver:Driver){
    setDetailDriver(driver)
    setDetailOpen(true)
    setDetailLoading(true)
    setDetailError('')
    setDetailProfile(null)
    try{
      const slug = slugifyName(driver.name || driver.driver_id)
      if(!slug){
        throw new Error('Driver profile unavailable')
      }
      const year = eligibility?.season_year
      const profile = await fetchDriverProfile(slug, year)
      setDetailProfile(profile || null)
    }catch(err:any){
      setDetailError(err.message || 'Unable to load driver details')
    }finally{
      setDetailLoading(false)
    }
  }

  function closeDriverDetails(){
    setDetailOpen(false)
  }

  function renderTier(label:string, key:'top'|'middle'|'bottom', drivers:Driver[]){
    const max = eligibility?.tiers?.[key]?.max_picks || 0
    const selectedCount = selection[key].length
    return (
      <section className="tier">
        <header>
          <h3>{label}</h3>
          <span className="chip">{selectedCount}/{max} picks</span>
        </header>
        <div className="driver-list">
          {drivers.map(driver => {
            const picked = selection[key].includes(driver.driver_id)
            const disabled = !picked && (selectedCount >= max || isSelected(driver.driver_id))
            return (
              <div key={driver.driver_id} className={`driver-card ${picked ? 'active' : ''}`}>
                <div>
                  <div className="driver-name">{formatDriverName(driver.name || driver.driver_id)}</div>
                  <div className="driver-meta">Rank {driver.rank} • {driver.remaining} starts left</div>
                </div>
                <div className="driver-actions">
                  <button className="ghost" onClick={()=>openDriverDetails(driver)}>Details</button>
                  <button disabled={disabled} onClick={()=>toggleDriver(key, driver.driver_id)}>
                    {picked ? 'Remove' : 'Add'}
                  </button>
                </div>
              </div>
            )
          })}
          {!drivers.length && <div className="empty">No eligible drivers left.</div>}
        </div>
      </section>
    )
  }

  return (
    <div className="page">
      <section className="panel hero">
        <div>
          <h2>Weekly Lineup Builder</h2>
          <p>Pick drivers by tier based on current standings. Lineups lock ahead of race time.</p>
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
        <h3>League Access</h3>
        <div className="grid two">
          <div>
            <label>New league</label>
            <div className="inline">
              <input value={leagueName} onChange={e=>setLeagueName(e.target.value)} placeholder="League name" />
              <button disabled={!token || busy} onClick={handleCreateLeague}>Create</button>
            </div>
          </div>
          <div>
            <label>Join by code</label>
            <div className="inline">
              <input value={leagueCode} onChange={e=>setLeagueCode(e.target.value)} placeholder="ABC123" />
              <button disabled={!token || busy} onClick={handleJoinLeague}>Join</button>
            </div>
          </div>
        </div>
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
      </section>

      <section className="panel">
        <div className="grid two">
          <div>
            <label>Race</label>
            <select value={raceId} onChange={e=>setRaceId(e.target.value)}>
              <option value="" disabled>Select a race</option>
              {races.map(r => (
                <option key={r.raceId} value={r.raceId}>
                  {r.name} {r.date ? `(${r.date.slice(0,10)})` : ''}
                </option>
              ))}
            </select>
          </div>
          <div className="inline end">
            <button disabled={!token || !leagueId || !raceId || busy} onClick={loadEligibility}>Load Eligibility</button>
          </div>
        </div>
        {eligibility && (
          <div className="notice">
            <div>Lock time: {eligibility.lock_time ? new Date(eligibility.lock_time).toLocaleString() : 'Unknown'}</div>
            <div>Status: {eligibility.locked ? 'Locked' : 'Open'}</div>
            <div>Max starts per driver: {eligibility.settings.max_starts_per_driver}</div>
          </div>
        )}
      </section>

      {eligibility && (
        <div className="grid three">
          {renderTier('Top Tier', 'top', eligibility.tiers?.top?.drivers || [])}
          {renderTier('Middle Tier', 'middle', eligibility.tiers?.middle?.drivers || [])}
          {renderTier('Bottom Tier', 'bottom', eligibility.tiers?.bottom?.drivers || [])}
        </div>
      )}

      {eligibility && (
        <section className="panel">
          <div className="summary">
            <div>
              <strong>Selected:</strong> {selection.top.length + selection.middle.length + selection.bottom.length} drivers
            </div>
            <button disabled={busy || eligibility.locked} onClick={submitLineup}>
              Save Lineup
            </button>
          </div>
          {status && <div className="success">{status}</div>}
        </section>
      )}

      {selectedLeague?.role === 'commissioner' && settingsDraft && (
        <section className="panel">
          <h3>Commissioner Settings</h3>
          <div className="grid three">
            <div>
              <label>Top picks</label>
              <input type="number" min="0" value={settingsDraft.top_pick_count} onChange={e=>setSettingsDraft({...settingsDraft, top_pick_count: e.target.value})} />
            </div>
            <div>
              <label>Middle picks</label>
              <input type="number" min="0" value={settingsDraft.middle_pick_count} onChange={e=>setSettingsDraft({...settingsDraft, middle_pick_count: e.target.value})} />
            </div>
            <div>
              <label>Bottom picks</label>
              <input type="number" min="0" value={settingsDraft.bottom_pick_count} onChange={e=>setSettingsDraft({...settingsDraft, bottom_pick_count: e.target.value})} />
            </div>
          </div>
          <div className="grid three">
            <div>
              <label>Top tier max rank</label>
              <input type="number" min="1" value={settingsDraft.top_rank_max} onChange={e=>setSettingsDraft({...settingsDraft, top_rank_max: e.target.value})} />
            </div>
            <div>
              <label>Middle tier max rank</label>
              <input type="number" min="1" value={settingsDraft.middle_rank_max} onChange={e=>setSettingsDraft({...settingsDraft, middle_rank_max: e.target.value})} />
            </div>
            <div>
              <label>Max starts per driver</label>
              <input type="number" min="1" value={settingsDraft.max_starts_per_driver} onChange={e=>setSettingsDraft({...settingsDraft, max_starts_per_driver: e.target.value})} />
            </div>
          </div>
          <div className="grid two">
            <div>
              <label>Lock hours before race</label>
              <input type="number" min="1" value={settingsDraft.lock_hours} onChange={e=>setSettingsDraft({...settingsDraft, lock_hours: e.target.value})} />
            </div>
            <div className="inline end">
              <button disabled={busy} onClick={saveSettings}>Save Settings</button>
            </div>
          </div>
          {status && <div className="success">{status}</div>}
        </section>
      )}

      {error && <div className="error">{error}</div>}

      {detailOpen && (
        <div className="drawer">
          <div className="drawer-card">
            <button className="close" onClick={closeDriverDetails}>Close</button>
            {detailDriver && (
              <div className="drawer-header">
                <div>
                  <div className="drawer-title">{formatDriverName(detailDriver.name || detailDriver.driver_id)}</div>
                  <div className="driver-meta">Rank {detailDriver.rank} • {detailDriver.remaining} starts left</div>
                </div>
                {(detailProfile?.photo_url || detailProfile?.car_number_image) && (
                  <div className="headshot-wrap">
                    {detailProfile?.photo_url && (
                      <img className="headshot" src={detailProfile.photo_url} alt={detailProfile.name || detailDriver.name || 'Driver'} />
                    )}
                    {detailProfile.car_number_image && (
                      <img className="car-number" src={detailProfile.car_number_image} alt="Car number" />
                    )}
                  </div>
                )}
              </div>
            )}
            {detailLoading && <div className="notice">Loading driver details...</div>}
            {detailError && <div className="error">{detailError}</div>}
            {!detailLoading && !detailError && (
              <>
                {detailProfile && (
                  <div className="panel">
                    <h3>Profile</h3>
                    <div className="driver-meta">{detailProfile.name || formatDriverName(detailDriver.name || detailDriver.driver_id)}</div>
                    {detailProfile.rank && <div className="driver-meta">Ranking: {detailProfile.rank}</div>}
                    {detailProfile.points && <div className="driver-meta">Points: {detailProfile.points}</div>}
                    {detailProfile.car_no && <div className="driver-meta">Car No: {detailProfile.car_no}</div>}
                    {detailProfile.dob && <div className="driver-meta">Born: {detailProfile.dob}</div>}
                    {detailProfile.hometown && <div className="driver-meta">Hometown: {detailProfile.hometown}</div>}
                    {detailProfile.team && <div className="driver-meta">Team: {detailProfile.team}</div>}
                    {detailProfile.crew_chief && <div className="driver-meta">Crew Chief: {detailProfile.crew_chief}</div>}
                    {detailProfile.bio && <div className="driver-meta">Bio: {detailProfile.bio}</div>}
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
