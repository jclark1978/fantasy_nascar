import { AudioManager } from '../audio/audio'
import { Renderer } from '../render/Renderer'
import { createRng } from '../utils/random'
import { hitBuilding, hitGorilla } from './collision'
import { updateProjectile, toVelocity } from './physics'
import { generateSkyline, spawnGorillas } from './worldgen'
import { GameSettings, GameState, WORLD_HEIGHT, WORLD_WIDTH } from './state'

export class Game {
  private state: GameState
  private renderer: Renderer
  private audio: AudioManager
  private raf?: number
  private lastTs = 0

  constructor(private ctx: CanvasRenderingContext2D, private settings: GameSettings, seed = Date.now()) {
    this.renderer = new Renderer(ctx)
    this.audio = new AudioManager()
    this.state = this.createInitialState(seed)
    this.setupRound()
  }

  private createInitialState(seed: number): GameState {
    return {
      seed,
      phase: 'SetupRound',
      currentPlayer: 1,
      round: 1,
      score: { 1: 0, 2: 0 },
      buildings: [],
      gorillas: [] as any,
      projectile: {
        active: false,
        position: { x: 0, y: 0 },
        velocity: { x: 0, y: 0 },
        rotation: 0,
        radius: 6,
      },
      explosion: { active: false, center: { x: 0, y: 0 }, radius: 34, age: 0 },
      wind: 0,
      shotInput: {
        1: { angle: 45, power: 65 },
        2: { angle: 45, power: 65 },
      },
    }
  }

  getState = () => this.state

  updateSettings(settings: GameSettings) {
    this.settings = settings
  }

  setupRound() {
    const rng = createRng(this.state.seed + this.state.round)
    this.state.buildings = generateSkyline(rng)
    this.state.gorillas = spawnGorillas(this.state.buildings)
    this.state.projectile.active = false
    this.state.explosion.active = false
    this.state.winner = undefined
    this.state.wind = this.settings.windEnabled ? (rng.next() - 0.5) * 120 : 0
    this.state.phase = 'AwaitInput'
  }

  start() {
    const tick = (ts: number) => {
      const dt = Math.min((ts - this.lastTs) / 1000 || 0, 1 / 30)
      this.lastTs = ts
      this.step(dt)
      this.renderer.render(this.state)
      this.raf = requestAnimationFrame(tick)
    }
    this.raf = requestAnimationFrame(tick)
  }

  stop() {
    if (this.raf) cancelAnimationFrame(this.raf)
  }

  setShotInput(player: 1 | 2, key: 'angle' | 'power', value: number) {
    if (this.state.phase !== 'AwaitInput') return
    if (player !== this.state.currentPlayer) return
    this.state.shotInput[player][key] = value
  }

  fire() {
    if (this.state.phase !== 'AwaitInput') return
    const shooter = this.state.currentPlayer === 1 ? this.state.gorillas[0] : this.state.gorillas[1]
    const input = this.state.shotInput[this.state.currentPlayer]
    const direction = this.state.currentPlayer === 1 ? 1 : -1
    const velocity = toVelocity(input.angle, input.power, direction)
    this.state.projectile = {
      ...this.state.projectile,
      active: true,
      position: { x: shooter.position.x, y: shooter.position.y - 20 },
      velocity,
      rotation: 0,
    }
    this.state.phase = 'ProjectileInFlight'
    this.audio.throwWhoosh()
  }

  private step(dt: number) {
    if (this.state.phase === 'ProjectileInFlight') {
      updateProjectile(this.state.projectile, dt, this.settings.gravity, this.state.wind)
      const p = this.state.projectile

      const building = hitBuilding(p.position, p.radius, this.state.buildings)
      const gorilla = hitGorilla(p.position, p.radius, this.state.gorillas)
      const outOfBounds = p.position.x < 0 || p.position.x > WORLD_WIDTH || p.position.y > WORLD_HEIGHT

      if (building || gorilla || outOfBounds) {
        this.state.projectile.active = false
        this.state.explosion = {
          ...this.state.explosion,
          active: true,
          center: { ...p.position },
          age: 0,
        }
        this.state.phase = 'ResolveExplosion'
        this.audio.explosion()

        if (gorilla) {
          const winner = gorilla.player === 1 ? 2 : 1
          this.state.winner = winner
          this.state.score[winner] += 1
        }
      }
    } else if (this.state.phase === 'ResolveExplosion') {
      this.state.explosion.age += dt
      if (this.state.explosion.age > 0.45) {
        this.state.explosion.active = false
        if (this.state.winner) {
          if (this.state.score[this.state.winner] >= this.settings.targetScore) {
            this.state.matchWinner = this.state.winner
            this.state.phase = 'MatchOver'
            this.audio.victory()
          } else {
            this.state.phase = 'RoundOver'
            setTimeout(() => {
              this.state.round += 1
              this.setupRound()
            }, 800)
          }
        } else {
          this.state.currentPlayer = this.state.currentPlayer === 1 ? 2 : 1
          this.state.phase = 'AwaitInput'
        }
      }
    }
  }

  restartRound() {
    if (this.state.phase === 'ProjectileInFlight') return
    this.setupRound()
  }

  newMatch() {
    this.state = this.createInitialState(Date.now())
    this.setupRound()
  }
}
