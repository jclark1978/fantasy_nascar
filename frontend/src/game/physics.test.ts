import { describe, expect, it } from 'vitest'
import { toVelocity, updateProjectile } from './physics'
import { Projectile } from './state'

describe('physics integration', () => {
  it('updates projectile position and velocity with gravity', () => {
    const projectile: Projectile = {
      active: true,
      position: { x: 0, y: 0 },
      velocity: { x: 10, y: -20 },
      rotation: 0,
      radius: 4,
    }

    updateProjectile(projectile, 0.5, 10, 0)
    expect(projectile.velocity.y).toBe(-15)
    expect(projectile.position.x).toBe(5)
    expect(projectile.position.y).toBe(-7.5)
  })

  it('computes launch velocity', () => {
    const v = toVelocity(45, 100, 1)
    expect(v.x).toBeGreaterThan(0)
    expect(v.y).toBeLessThan(0)
  })
})
