export class AudioManager {
  private ctx?: AudioContext

  private beep(freq: number, duration = 0.12, type: OscillatorType = 'sine') {
    if (typeof window === 'undefined') return
    this.ctx ??= new AudioContext()
    const osc = this.ctx.createOscillator()
    const gain = this.ctx.createGain()
    osc.type = type
    osc.frequency.value = freq
    gain.gain.value = 0.08
    osc.connect(gain)
    gain.connect(this.ctx.destination)
    osc.start()
    osc.stop(this.ctx.currentTime + duration)
  }

  throwWhoosh() {
    this.beep(240, 0.06, 'triangle')
  }

  explosion() {
    this.beep(70, 0.22, 'sawtooth')
  }

  victory() {
    this.beep(500, 0.1)
    setTimeout(() => this.beep(660, 0.1), 80)
  }
}
