const API_BASE = import.meta.env.VITE_API_BASE || `http://${window.location.hostname}:8000`

async function getJSON(path: string, opts: RequestInit = {}){
  const res = await fetch(API_BASE + path, opts)
  if(!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function fetchRaces(year:number = new Date().getFullYear()){
  return getJSON(`/races/upcoming?year=${year}`)
}

export async function guestLogin(){
  return getJSON('/auth/guest', {method:'POST'})
}

export async function registerUser(email:string, password:string){
  return getJSON('/auth/register', {method:'POST', headers:{'content-type':'application/json'}, body: JSON.stringify({email, password})})
}

export async function loginUser(email:string, password:string){
  return getJSON('/auth/login', {method:'POST', headers:{'content-type':'application/json'}, body: JSON.stringify({email, password})})
}

export async function createPick(token:string, pick:{race_id:string, driver_id:string}){
  return getJSON('/picks', {method:'POST', headers:{'content-type':'application/json','authorization':'Bearer '+token}, body: JSON.stringify(pick)})
}

export async function myPicks(token:string){
  return getJSON('/picks/me', {headers:{'authorization':'Bearer '+token}})
}

export async function createLeague(token:string, payload:{name:string}){
  return getJSON('/leagues', {method:'POST', headers:{'content-type':'application/json','authorization':'Bearer '+token}, body: JSON.stringify(payload)})
}

export async function joinLeague(token:string, payload:{code:string}){
  return getJSON('/leagues/join', {method:'POST', headers:{'content-type':'application/json','authorization':'Bearer '+token}, body: JSON.stringify(payload)})
}

export async function fetchLeagues(token:string){
  return getJSON('/leagues/me', {headers:{'authorization':'Bearer '+token}})
}

export async function fetchEligibility(token:string, params:{league_id:number, race_id:string, year?:number}){
  const qs = new URLSearchParams({league_id: String(params.league_id), race_id: params.race_id})
  if(params.year){ qs.set('year', String(params.year)) }
  return getJSON('/lineups/eligible?' + qs.toString(), {headers:{'authorization':'Bearer '+token}})
}

export async function saveLineup(token:string, payload:{league_id:number, race_id:string, season_year:number, entries:{driver_id:string, tier:string}[]}){
  return getJSON('/lineups', {method:'POST', headers:{'content-type':'application/json','authorization':'Bearer '+token}, body: JSON.stringify(payload)})
}

export async function updateLeagueSettings(token:string, leagueId:number, payload:any){
  return getJSON(`/leagues/${leagueId}/settings`, {method:'PATCH', headers:{'content-type':'application/json','authorization':'Bearer '+token}, body: JSON.stringify(payload)})
}

export async function fetchStandings(year:number, series:number = 1){
  return getJSON(`/standings/drivers?year=${year}&series=${series}`)
}

export async function fetchResults(year:number, series:number = 1){
  return getJSON(`/results?year=${year}&series=${series}`)
}

export async function fetchDriverStats(driverId:string){
  return getJSON(`/drivers/${driverId}/stats`)
}

export async function fetchDriverInfo(driverId:string){
  return getJSON(`/drivers/${driverId}/info`)
}

export async function fetchDriverPhotos(driverId:string){
  return getJSON(`/drivers/${driverId}/photos`)
}
