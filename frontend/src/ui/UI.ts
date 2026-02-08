import { GameSettings, GRAVITY_BY_PRESET, GravityPreset, ShotInput } from '../game/state'

const SETTINGS_KEY = 'gorillas-settings-v1'

export const loadSettings = (): GameSettings => {
  const defaults: GameSettings = {
    gravityPreset: 'Earth',
    gravity: GRAVITY_BY_PRESET.Earth,
    windEnabled: true,
    targetScore: 3,
  }
  try {
    const raw = localStorage.getItem(SETTINGS_KEY)
    if (!raw) return defaults
    return { ...defaults, ...JSON.parse(raw) }
  } catch {
    return defaults
  }
}

export const saveSettings = (settings: GameSettings) => {
  localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings))
}

export const gravityFromPreset = (preset: GravityPreset) => GRAVITY_BY_PRESET[preset]

export const clampShotInput = (input: ShotInput) => ({
  angle: Math.max(5, Math.min(85, input.angle)),
  power: Math.max(10, Math.min(150, input.power)),
})
