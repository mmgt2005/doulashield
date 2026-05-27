const TIMEOUT_MS = 15 * 60 * 1000   // 15 minutes
const WARNING_MS = 14 * 60 * 1000   // show warning at 14 minutes

const ACTIVITY_EVENTS = ['mousemove', 'keydown', 'click', 'scroll', 'touchstart'] as const

export class SessionTimeoutManager {
  private timer: ReturnType<typeof setTimeout> | null = null
  private warningTimer: ReturnType<typeof setTimeout> | null = null
  private readonly onTimeout: () => void
  private readonly onWarning: () => void
  private readonly onActivity: () => void

  constructor(onTimeout: () => void, onWarning: () => void) {
    this.onTimeout = onTimeout
    this.onWarning = onWarning
    this.onActivity = () => this.reset()
  }

  start(): void {
    ACTIVITY_EVENTS.forEach((e) =>
      document.addEventListener(e, this.onActivity, { passive: true })
    )
    this.reset()
  }

  reset(): void {
    if (this.timer) clearTimeout(this.timer)
    if (this.warningTimer) clearTimeout(this.warningTimer)
    this.warningTimer = setTimeout(this.onWarning, WARNING_MS)
    this.timer = setTimeout(this.onTimeout, TIMEOUT_MS)
  }

  destroy(): void {
    if (this.timer) clearTimeout(this.timer)
    if (this.warningTimer) clearTimeout(this.warningTimer)
    ACTIVITY_EVENTS.forEach((e) =>
      document.removeEventListener(e, this.onActivity)
    )
  }
}
