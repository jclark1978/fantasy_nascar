import { useEffect, useMemo, useRef, useState } from 'react'
import { Game } from '../game/Game'
import { GameSettings, GRAVITY_BY_PRESET, GravityPreset, WORLD_HEIGHT, WORLD_WIDTH } from '../game/state'
import { clampShotInput, gravityFromPreset, loadSettings, saveSettings } from '../ui/UI'

export default function GorillasPage() {
  const canvasRef = useRef<HTMLCanvasElement | null>(null)
  const gameRef = useRef<Game | null>(null)
  const [settings, setSettings] = useState<GameSettings>(() => loadSettings())
  const [tick, setTick] = useState(0)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    const game = new Game(ctx, settings)
    gameRef.current = game
    game.start()

    const i = setInterval(() => setTick((x) => x + 1), 100)
    const onKey = (e: KeyboardEvent) => {
      const game = gameRef.current
      if (!game) return
      const state = game.getState()
      const shot = { ...state.shotInput[state.currentPlayer] }
      if (e.key === 'ArrowUp') shot.angle += 1
      if (e.key === 'ArrowDown') shot.angle -= 1
      if (e.key === 'ArrowRight') shot.power += 2
      if (e.key === 'ArrowLeft') shot.power -= 2
      if (e.key === 'Enter') game.fire()
      if (e.key.toLowerCase() === 'r') game.restartRound()
      if (e.key.toLowerCase() === 'n') game.newMatch()
      const next = clampShotInput(shot)
      game.setShotInput(state.currentPlayer, 'angle', next.angle)
      game.setShotInput(state.currentPlayer, 'power', next.power)
    }
    window.addEventListener('keydown', onKey)

    return () => {
      clearInterval(i)
      window.removeEventListener('keydown', onKey)
      game.stop()
    }
  }, [])

  useEffect(() => {
    gameRef.current?.updateSettings(settings)
    saveSettings(settings)
  }, [settings])

  const state = gameRef.current?.getState()
  const currentInput = state ? state.shotInput[state.currentPlayer] : { angle: 45, power: 65 }

  const presets = useMemo(() => Object.keys(GRAVITY_BY_PRESET) as GravityPreset[], [])

  return (
    <div className="page gorillas-page">
      <section className="panel gorillas-layout">
        <canvas ref={canvasRef} width={WORLD_WIDTH} height={WORLD_HEIGHT} className="gorillas-canvas" />
        <aside className="gorillas-controls">
          <h2>Gorillas: Modern</h2>
          <p className="muted">Turn: Player {state?.currentPlayer ?? 1} · Phase: {state?.phase ?? 'Loading'}</p>
          <p className="muted">Score P1 {state?.score[1] ?? 0} - {state?.score[2] ?? 0} P2</p>

          <label>Angle: {Math.round(currentInput.angle)}°</label>
          <input type="range" min={5} max={85} value={currentInput.angle}
            onChange={(e) => gameRef.current?.setShotInput(state!.currentPlayer, 'angle', Number(e.target.value))} />

          <label>Power: {Math.round(currentInput.power)}</label>
          <input type="range" min={10} max={150} value={currentInput.power}
            onChange={(e) => gameRef.current?.setShotInput(state!.currentPlayer, 'power', Number(e.target.value))} />

          <label>Gravity Preset</label>
          <select value={settings.gravityPreset} onChange={(e) => {
            const preset = e.target.value as GravityPreset
            setSettings((s) => ({ ...s, gravityPreset: preset, gravity: gravityFromPreset(preset) }))
          }}>
            {presets.map((preset) => <option key={preset} value={preset}>{preset}</option>)}
          </select>

          <label>Gravity ({settings.gravity.toFixed(0)})</label>
          <input type="range" min={30} max={280} value={settings.gravity}
            onChange={(e) => setSettings((s) => ({ ...s, gravity: Number(e.target.value), gravityPreset: 'Earth' }))} />

          <label className="checkbox-row">
            <input
              type="checkbox"
              checked={settings.windEnabled}
              onChange={(e) => setSettings((s) => ({ ...s, windEnabled: e.target.checked }))}
            />
            Wind enabled ({Math.round(state?.wind ?? 0)})
          </label>

          <div className="inline">
            <button onClick={() => gameRef.current?.fire()} disabled={state?.phase !== 'AwaitInput'}>Fire</button>
            <button className="ghost" onClick={() => gameRef.current?.restartRound()}>Restart Round (R)</button>
            <button className="ghost" onClick={() => gameRef.current?.newMatch()}>New Match (N)</button>
          </div>
          <p className="muted">Keyboard: ↑/↓ angle, ←/→ power, Enter fire.</p>
          <small className="muted">UI refresh tick: {tick}</small>
        </aside>
      </section>
    </div>
  )
}
