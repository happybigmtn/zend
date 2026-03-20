# Zend Design System

Zend should feel like a private household control panel, not a crypto casino and
not a generic SaaS dashboard. The emotional target is calm trust. Users should
feel that the system is local, legible, and respectful of risk.

## Product Feel

Three qualities govern every interface decision:

- calm: no frantic surfaces, no speculative-market energy, no glowing casino UI
- domestic: the product should feel closer to a thermostat or power panel than a
  developer console
- trustworthy: every permission, action, and receipt must be explicit

## Typography

- headings: `Space Grotesk`, weight 600 or 700
- body: `IBM Plex Sans`, weight 400 or 500
- numeric and operational data: `IBM Plex Mono`, weight 500

Do not use Inter, Roboto, Arial, or system-default stacks as the primary design
language. Operational numbers and device identifiers must use the mono face so
they read as precise. Body copy should stay plain and unshowy.

## Color System

- `Basalt`: `#16181B` for primary dark surface
- `Slate`: `#23272D` for elevated surfaces
- `Mist`: `#EEF1F4` for light backgrounds and cards in light mode
- `Moss`: `#486A57` for healthy or stable system state
- `Amber`: `#D59B3D` for caution or pending actions
- `Signal Red`: `#B44C42` for destructive or degraded state
- `Ice`: `#B8D7E8` for informational highlights

Avoid neon greens, exchange-red candlesticks, and purple SaaS gradients. Zend
should look expensive, domestic, and grounded.

## Layout

Mobile is the primary viewport. The default experience is single-column with
large touch targets and a clear thumb zone.

The first product slice uses four primary destinations:

- `Home`: the live miner overview and top controls
- `Inbox`: operational receipts, alerts, Hermes summaries, and messages
- `Agent`: delegated Hermes status and approvals
- `Device`: trust, pairing, permissions, and recovery

Primary navigation should be a bottom tab bar on mobile. On larger screens, the
same destinations may move to a left rail, but the order must stay stable.

## Component Vocabulary

Zend should favor a small number of components used consistently:

- `Status Hero`: the large top block on `Home` showing miner state, mode, and
  freshness
- `Mode Switcher`: a segmented control for paused, balanced, performance
- `Receipt Card`: a concise event entry with clear origin, time, and outcome
- `Permission Pill`: a clear observe or control chip
- `Trust Sheet`: a modal or sheet used during pairing and capability grants
- `Alert Banner`: short, high-signal warning surface

Avoid generic feature-card grids, decorative icon farms, or dashboard widgets
that exist only because dashboards are expected to have widgets.

## Motion

Motion is functional, not ornamental.

- state changes should use short fades and position shifts
- receipts may slide in subtly from the edge
- mode changes may pulse once to confirm the new state
- destructive states should not shake or flash aggressively

Respect `prefers-reduced-motion`. If motion is disabled, every transition must
still remain understandable from layout and copy alone.

## Accessibility

- touch targets: minimum `44x44` logical pixels
- body text: minimum equivalent of `16px`
- contrast: WCAG AA minimum for all text and controls
- keyboard support: complete on larger screens and desktop-class clients
- screen readers: landmark regions for Home, Inbox, Agent, and Device
- live regions: new receipts and alerts must be announced politely
- color is never the only signal for miner health or action results

## AI Slop Guardrails

The following patterns are banned unless a future design review explicitly
justifies them:

- hero section with slogan + CTA over a generic gradient
- three-column feature grid with stock icons
- glassmorphism control panels
- crypto exchange aesthetics
- “clean modern dashboard” with unnamed widgets
- empty states that say only “No items found”

Every empty state needs warmth, context, and a primary next action.
