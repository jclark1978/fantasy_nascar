import { GameState, WORLD_HEIGHT, WORLD_WIDTH } from '../game/state'

export class Renderer {
  constructor(private ctx: CanvasRenderingContext2D) {}

  render(state: GameState) {
    this.drawBackground()
    this.drawBuildings(state)
    this.drawGorillas(state)
    this.drawProjectile(state)
    this.drawExplosion(state)
    if (state.phase === 'RoundOver' || state.phase === 'MatchOver') {
      this.drawBanner(state)
    }
  }

  private drawBackground() {
    const g = this.ctx.createLinearGradient(0, 0, 0, WORLD_HEIGHT)
    g.addColorStop(0, '#0b1f3f')
    g.addColorStop(1, '#172033')
    this.ctx.fillStyle = g
    this.ctx.fillRect(0, 0, WORLD_WIDTH, WORLD_HEIGHT)
  }

  private drawBuildings(state: GameState) {
    for (const b of state.buildings) {
      this.ctx.fillStyle = '#232d41'
      this.ctx.fillRect(b.x, b.y, b.width, b.height)
      for (const w of b.windows) {
        this.ctx.fillStyle = w.lit ? '#ffc857' : '#31415c'
        this.ctx.fillRect(w.x, w.y, 7, 10)
      }
    }
  }

  private drawGorillas(state: GameState) {
    for (const g of state.gorillas) {
      this.ctx.fillStyle = g.player === 1 ? '#7bdff2' : '#f7a072'
      this.ctx.beginPath()
      this.ctx.arc(g.position.x, g.position.y, g.radius, 0, Math.PI * 2)
      this.ctx.fill()
    }
  }

  private drawProjectile(state: GameState) {
    if (!state.projectile.active) return
    const p = state.projectile
    this.ctx.save()
    this.ctx.translate(p.position.x, p.position.y)
    this.ctx.rotate(p.rotation)
    this.ctx.fillStyle = '#ffe066'
    this.ctx.fillRect(-11, -4, 22, 8)
    this.ctx.restore()
  }

  private drawExplosion(state: GameState) {
    if (!state.explosion.active) return
    const e = state.explosion
    this.ctx.fillStyle = `rgba(255, 140, 66, ${Math.max(0, 1 - e.age * 2)})`
    this.ctx.beginPath()
    this.ctx.arc(e.center.x, e.center.y, e.radius * (1 + e.age * 2), 0, Math.PI * 2)
    this.ctx.fill()
  }

  private drawBanner(state: GameState) {
    this.ctx.fillStyle = 'rgba(0,0,0,0.5)'
    this.ctx.fillRect(0, WORLD_HEIGHT / 2 - 40, WORLD_WIDTH, 80)
    this.ctx.fillStyle = '#fff'
    this.ctx.font = 'bold 36px sans-serif'
    const message =
      state.phase === 'MatchOver'
        ? `Player ${state.matchWinner} wins the match!`
        : `Player ${state.winner} wins the round!`
    this.ctx.fillText(message, WORLD_WIDTH / 2 - 220, WORLD_HEIGHT / 2 + 12)
  }
}
