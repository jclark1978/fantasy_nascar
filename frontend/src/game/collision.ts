import { Building, Gorilla, Vec2 } from './state'

export const circleRectCollision = (center: Vec2, radius: number, rect: Building) => {
  const closestX = Math.max(rect.x, Math.min(center.x, rect.x + rect.width))
  const closestY = Math.max(rect.y, Math.min(center.y, rect.y + rect.height))
  const dx = center.x - closestX
  const dy = center.y - closestY
  return dx * dx + dy * dy <= radius * radius
}

export const circleCircleCollision = (a: Vec2, ar: number, b: Vec2, br: number) => {
  const dx = a.x - b.x
  const dy = a.y - b.y
  const r = ar + br
  return dx * dx + dy * dy <= r * r
}

export const hitBuilding = (position: Vec2, radius: number, buildings: Building[]) =>
  buildings.find((b) => circleRectCollision(position, radius, b))

export const hitGorilla = (position: Vec2, radius: number, gorillas: Gorilla[]) =>
  gorillas.find((g) => circleCircleCollision(position, radius, g.position, g.radius))
