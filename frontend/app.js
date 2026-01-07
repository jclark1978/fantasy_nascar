const API_BASE = location.origin.replace(/:\d+$/, ':8000')

function setStatus(msg){ document.getElementById('status').textContent = msg }

async function guestLogin(){
  setStatus('Logging in as guest...')
  const res = await fetch(API_BASE + '/auth/guest', {method:'POST'})
  const data = await res.json()
  localStorage.setItem('token', data.access_token)
  setStatus('Logged in as guest')
  await loadRaces()
  await loadPicks()
}

async function seedLogin(){
  setStatus('Seeding test user...')
  // call seed script via backend: we rely on developer running backend/seed.py locally; fall back to register
  try{
    const r = await fetch(API_BASE + '/auth/login', {method:'POST', headers:{'content-type':'application/json'}, body: JSON.stringify({email:'test@example.com', password:'password'})})
    if(r.ok){ const j = await r.json(); localStorage.setItem('token', j.access_token); setStatus('Logged in as test@example.com'); await loadRaces(); await loadPicks(); return }
  }catch(e){}
  // try register
  const r2 = await fetch(API_BASE + '/auth/register', {method:'POST', headers:{'content-type':'application/json'}, body: JSON.stringify({email:'test@example.com', password:'password'})})
  if(r2.ok){ const j = await r2.json(); localStorage.setItem('token', j.access_token); setStatus('Registered and logged in'); await loadRaces(); await loadPicks(); return }
  setStatus('Seed/register failed — run backend/seed.py and try guest login')
}

async function loadRaces(){
  const list = document.getElementById('race-list'); list.innerHTML = 'Loading...'
  const res = await fetch(API_BASE + '/races/upcoming')
  const races = await res.json()
  list.innerHTML = ''
  for(const r of races){
    const li = document.createElement('li')
    li.textContent = `${r.name} — ${new Date(r.date||'').toLocaleString()}`
    const btn = document.createElement('button')
    btn.textContent = 'Pick first driver (demo)'
    btn.onclick = ()=> pickDriver(r.raceId, 'demo-driver')
    li.appendChild(btn)
    list.appendChild(li)
  }
}

async function pickDriver(raceId, driverId){
  const token = localStorage.getItem('token')
  if(!token){ setStatus('Please login first'); return }
  const res = await fetch(API_BASE + '/picks', {method:'POST', headers:{'content-type':'application/json','authorization':'Bearer '+token}, body: JSON.stringify({race_id:raceId, driver_id:driverId})})
  if(res.ok){ setStatus('Pick saved'); await loadPicks(); return }
  const txt = await res.text()
  setStatus('Pick failed: ' + txt)
}

async function loadPicks(){
  const token = localStorage.getItem('token')
  const list = document.getElementById('pick-list'); list.innerHTML = ''
  if(!token){ list.innerHTML = '<em>Login to see picks</em>'; return }
  const res = await fetch(API_BASE + '/picks/me', {headers:{'authorization':'Bearer '+token}})
  if(!res.ok){ list.innerHTML = '<em>Failed to load picks</em>'; return }
  const picks = await res.json()
  for(const p of picks){ const li = document.createElement('li'); li.textContent = `${p.race_id} → ${p.driver_id} (${new Date(p.created_at).toLocaleString()})`; list.appendChild(li) }
}

document.getElementById('guest').addEventListener('click', guestLogin)
document.getElementById('seed-login').addEventListener('click', seedLogin)

(async ()=>{ await loadRaces(); await loadPicks() })()
