import { Building, Gorilla, WORLD_HEIGHT, WORLD_WIDTH } from './state'
import { RNG } from '../utils/random'

export const generateSkyline = (rng: RNG): Building[] => {
  const buildings: Building[] = []
  let x = 0
  while (x < WORLD_WIDTH) {
    const width = Math.min(rng.int(40, 120), WORLD_WIDTH - x)
    const height = rng.int(150, 550)
    const y = WORLD_HEIGHT - height
    const windows = []
    for (let wy = y + 20; wy < WORLD_HEIGHT - 20; wy += 24) {
      for (let wx = x + 10; wx < x + width - 10; wx += 18) {
        windows.push({ x: wx, y: wy, lit: rng.next() > 0.45 })
      }
    }
    buildings.push({ x, y, width, height, windows })
    x += width
  }
  return buildings
}

const pickBuilding = (buildings: Building[], leftSide: boolean) => {
  const min = leftSide ? 0 : Math.floor(buildings.length * 0.8)
  const max = leftSide ? Math.max(0, Math.floor(buildings.length * 0.2) - 1) : buildings.length - 1
  return buildings[Math.floor((min + max) / 2)]
}

export const spawnGorillas = (buildings: Building[]): [Gorilla, Gorilla] => {
  const left = pickBuilding(buildings, true)
  const right = pickBuilding(buildings, false)
  return [
    {
      player: 1,
      radius: 24,
      health: 100,
      position: { x: left.x + left.width / 2, y: left.y - 24 },
    },
    {
      player: 2,
      radius: 24,
      health: 100,
      position: { x: right.x + right.width / 2, y: right.y - 24 },
    },
  ]
}
