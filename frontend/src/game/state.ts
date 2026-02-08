export type GamePhase =
  | 'SetupRound'
  | 'AwaitInput'
  | 'ProjectileInFlight'
  | 'ResolveExplosion'
  | 'RoundOver'
  | 'MatchOver'

export type GravityPreset = 'Earth' | 'Moon' | 'Mars'

export interface Vec2 {
  x: number
  y: number
}

export interface Building {
  x: number
  y: number
  width: number
  height: number
  windows: Array<{ x: number; y: number; lit: boolean }>
}

export interface Gorilla {
  player: 1 | 2
  position: Vec2
  radius: number
  health: number
}

export interface Projectile {
  active: boolean
  position: Vec2
  velocity: Vec2
  rotation: number
  radius: number
}

export interface Explosion {
  active: boolean
  center: Vec2
  radius: number
  age: number
}

export interface ShotInput {
  angle: number
  power: number
}

export interface GameSettings {
  gravityPreset: GravityPreset
  gravity: number
  windEnabled: boolean
  targetScore: number
}

export interface GameState {
  seed: number
  phase: GamePhase
  currentPlayer: 1 | 2
  round: number
  score: Record<1 | 2, number>
  buildings: Building[]
  gorillas: [Gorilla, Gorilla]
  projectile: Projectile
  explosion: Explosion
  wind: number
  shotInput: Record<1 | 2, ShotInput>
  winner?: 1 | 2
  matchWinner?: 1 | 2
}

export const WORLD_WIDTH = 1280
export const WORLD_HEIGHT = 720

export const GRAVITY_BY_PRESET: Record<GravityPreset, number> = {
  Earth: 240,
  Moon: 60,
  Mars: 90,
}
