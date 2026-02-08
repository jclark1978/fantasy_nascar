import { Projectile } from './state'

export const toVelocity = (angleDeg: number, power: number, direction: 1 | -1) => {
  const rad = (angleDeg * Math.PI) / 180
  const speed = power * 6
  return {
    x: Math.cos(rad) * speed * direction,
    y: -Math.sin(rad) * speed,
  }
}

export const updateProjectile = (
  projectile: Projectile,
  dt: number,
  gravity: number,
  wind: number,
) => {
  if (!projectile.active) return projectile
  projectile.velocity.x += wind * dt
  projectile.velocity.y += gravity * dt
  projectile.position.x += projectile.velocity.x * dt
  projectile.position.y += projectile.velocity.y * dt
  projectile.rotation += dt * 14
  return projectile
}
