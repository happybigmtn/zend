# Design Checklist

**Status:** Implementation Reference for Milestone 1
**Last Updated:** 2026-03-19

## Typography

- [ ] Use Space Grotesk for headings
- [ ] Use IBM Plex Sans for body text
- [ ] Use IBM Plex Mono for code/status values

## Color

- [ ] Calm, domestic palette - no neon or trading-terminal colors
- [ ] Primary actions are accessible and consistent
- [ ] Status states use color + icon (never color alone)

## Layout

- [ ] Mobile-first single column layout
- [ ] Bottom tab bar always reachable by thumb
- [ ] Status Hero is the dominant home element
- [ ] Mode Switcher is prominent but secondary to status

## Components

### Status Hero
- [ ] Shows miner state (running/stopped/offline)
- [ ] Shows active mode (paused/balanced/performance)
- [ ] Shows snapshot freshness timestamp
- [ ] Visual distinction between fresh and stale

### Mode Switcher
- [ ] Three modes: paused, balanced, performance
- [ ] Explicit confirmation before mode change
- [ ] Shows pending state during change
- [ ] Disabled for observe-only clients

### Receipt Card
- [ ] One consistent style for all operational events
- [ ] Shows timestamp, type, and outcome
- [ ] Tappable for details

### Trust Sheet
- [ ] Clear explanation of observe vs control
- [ ] Named device presentation
- [ ] Easy revoke path

### Permission Pill
- [ ] Consistent vocabulary: "observe" and "control"
- [ ] Visual distinction between the two

## Interaction States

- [ ] Loading: skeleton + trust copy
- [ ] Empty: warm "nothing yet" copy + first action
- [ ] Error: clear failure with retry
- [ ] Success: clear confirmation
- [ ] Partial: warning state with explanation

## Accessibility

- [ ] Minimum 44x44 touch targets
- [ ] Body text at least 16px equivalent
- [ ] All states announced by text and icon
- [ ] Polite live region for new receipts
- [ ] Full keyboard navigation on large screens
- [ ] Screen-reader landmarks for Home, Inbox, Agent, Device
- [ ] Reduced-motion fallback

## AI Slop Guardrails

- [ ] No generic crypto-dashboard widgets
- [ ] No hero sections with abstract gradients
- [ ] No three-card feature grids
- [ ] No decorative icon farms
- [ ] No "No items found" without next step
