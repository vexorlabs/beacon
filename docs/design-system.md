# Beacon Design System

> Living reference for developers and AI agents building Beacon's frontend.
> Inspired by Linear's design language — dark-first, information-dense, refined.

---

## Philosophy

- **Dark-first.** The default theme is dark. Every color choice is optimized for dark backgrounds.
- **Information-dense.** This is a developer tool. Maximize useful information per pixel.
- **Quiet surfaces, loud actions.** Backgrounds and text are muted; primary actions (buttons, links, focus rings) use the accent color.
- **Consistent, not creative.** Every component should feel like it belongs. Reuse tokens, don't invent new values.

---

## Color Tokens

All colors use **oklch** with a subtle blue-purple hue (272 on the hue wheel) for neutrals, and a saturated blue-purple (275) for accents.

### Dark Theme (Default)

| Token | Value | Usage |
|-------|-------|-------|
| `--background` | `oklch(0.145 0.004 272)` | App background |
| `--foreground` | `oklch(0.985 0.002 272)` | Primary text |
| `--card` | `oklch(0.185 0.008 272)` | Card/panel backgrounds |
| `--card-foreground` | `oklch(0.985 0.002 272)` | Text on cards |
| `--popover` | `oklch(0.200 0.010 272)` | Popover/dropdown backgrounds |
| `--popover-foreground` | `oklch(0.985 0.002 272)` | Text on popovers |
| `--primary` | `oklch(0.500 0.200 275)` | Accent (CTA buttons, links, focus rings) |
| `--primary-foreground` | `oklch(0.985 0.002 272)` | Text on accent backgrounds |
| `--secondary` | `oklch(0.200 0.012 272)` | Hover backgrounds, toggle active states |
| `--secondary-foreground` | `oklch(0.985 0.002 272)` | Text on secondary backgrounds |
| `--muted` | `oklch(0.200 0.012 272)` | Muted backgrounds (same as secondary) |
| `--muted-foreground` | `oklch(0.600 0.006 272)` | Tertiary/muted text, placeholders |
| `--accent` | `oklch(0.200 0.012 272)` | Accent backgrounds (same as secondary) |
| `--accent-foreground` | `oklch(0.985 0.002 272)` | Text on accent backgrounds |
| `--destructive` | `oklch(0.704 0.191 22.216)` | Error/destructive actions |
| `--border` | `oklch(0.300 0.012 272)` | Borders, dividers |
| `--input` | `oklch(0.300 0.012 272)` | Input borders |
| `--ring` | `oklch(0.500 0.200 275)` | Focus rings |

### Sidebar

| Token | Value | Usage |
|-------|-------|-------|
| `--sidebar` | `oklch(0.130 0.004 272)` | Sidebar background (slightly darker than app) |
| `--sidebar-foreground` | `oklch(0.985 0.002 272)` | Sidebar text |
| `--sidebar-primary` | `oklch(0.500 0.200 275)` | Sidebar active accent |
| `--sidebar-accent` | `oklch(0.200 0.012 272)` | Sidebar hover/active item bg |
| `--sidebar-border` | `oklch(0.300 0.012 272)` | Sidebar borders |

### Span Type Colors (Graph Nodes)

These use Tailwind utility classes with dark-mode-friendly opacity:

| Span Type | Background | Border | Text |
|-----------|-----------|--------|------|
| `llm_call` | `bg-blue-950/40` | `border-blue-500/40` | `text-blue-300` |
| `tool_use` | `bg-emerald-950/40` | `border-emerald-500/40` | `text-emerald-300` |
| `browser_action` | `bg-orange-950/40` | `border-orange-500/40` | `text-orange-300` |
| `file_operation` | `bg-amber-950/40` | `border-amber-500/40` | `text-amber-300` |
| `shell_command` | `bg-purple-950/40` | `border-purple-500/40` | `text-purple-300` |
| `agent_step` | `bg-zinc-800/40` | `border-zinc-500/40` | `text-zinc-300` |
| `chain` | `bg-zinc-800/40` | `border-zinc-500/40` | `text-zinc-300` |
| `custom` | `bg-zinc-800/40` | `border-zinc-500/40` | `text-zinc-300` |

### Usage Guidelines

- Use `bg-background` for app-level background
- Use `bg-card` for elevated surfaces (panels, cards, detail views)
- Use `bg-secondary` for hover/active states
- Use `text-foreground` for primary text
- Use `text-muted-foreground` for secondary/helper text
- Use `text-primary` for accent-colored text (links, active states)
- Use `border-border` for all borders
- Never hardcode color values — always use CSS variable tokens or the Tailwind classes they map to

---

## Typography

### Font Stack

```css
font-family: 'Inter Variable', 'Inter', -apple-system, BlinkMacSystemFont,
  'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans',
  'Helvetica Neue', sans-serif;
```

For monospace (code, terminal output):
```css
font-family: 'JetBrains Mono', 'SF Mono', 'Fira Code', ui-monospace, monospace;
```

### Type Scale

| Name | Size | Tailwind | Usage |
|------|------|----------|-------|
| xs | 11px | `text-[11px]` | Keyboard hints, timestamps, micro labels |
| sm | 12px | `text-xs` | Buttons, metadata, secondary labels |
| base | 13px | `text-[13px]` | Body text, nav items, list items (app default) |
| md | 14px | `text-sm` | Section headers, emphasis text |
| lg | 16px | `text-base` | Page titles, dialog headers |
| xl | 20px | `text-xl` | Dashboard headings |
| 2xl | 24px | `text-2xl` | Hero headings |

### Font Weights

| Weight | Value | Usage |
|--------|-------|-------|
| Normal | 400 | Body text, descriptions |
| Medium | 500 | Buttons, labels, nav items (active) |
| Semibold | 600 | Headings, emphasis |

### Line Heights

- Tight: `1.2` — headings
- Normal: `1.5` — body text (default)
- Relaxed: `1.625` — long-form content

---

## Spacing

Use Tailwind's default spacing scale. Prefer these values for consistency:

| Token | px | Usage |
|-------|-----|-------|
| `0.5` | 2px | Icon-to-text micro gap |
| `1` | 4px | Tight internal padding |
| `1.5` | 6px | Nav item horizontal padding |
| `2` | 8px | Standard small gap, icon margins |
| `3` | 12px | Component internal padding |
| `4` | 16px | Section padding, card padding |
| `6` | 24px | Large section gaps |
| `8` | 32px | Page-level padding |

---

## Border & Radius

### Border Width

- **Standard:** `1px` — most borders (`border` utility)
- **Hairline:** `0.5px` — subtle dividers (use `border-[0.5px]`)

### Border Radius

| Token | Value | Usage |
|-------|-------|-------|
| `--radius` | `0.25rem` (4px) | Default — buttons, inputs, cards, nav items |
| `rounded-sm` | 2px | Tight elements |
| `rounded-md` | 4px | Standard (same as default) |
| `rounded-lg` | 6px | Larger cards, modals |
| `rounded-xl` | 8px | Feature cards |
| `rounded-full` | 9999px | Pills, avatars |

---

## Shadows

Dark themes need stronger shadows for depth perception:

| Name | Value | Usage |
|------|-------|-------|
| sm | `0 1px 2px oklch(0 0 0 / 0.3)` | Subtle elevation (buttons) |
| md | `0 2px 8px oklch(0 0 0 / 0.4)` | Cards, panels |
| lg | `0 4px 16px oklch(0 0 0 / 0.5)` | Modals, popovers |

---

## Component Patterns

### Nav Item (Sidebar)

```
Height: 28px
Padding: 0 6px
Icon: 14px, text-muted-foreground
Gap (icon to text): 8px (gap-2)
Text: 13px, font-normal
Active: bg-secondary, text-foreground, font-medium
Inactive: transparent bg, text-muted-foreground
Hover: bg-secondary/50, text-foreground
Transition: 0.15s colors
Border radius: rounded-md (4px)
```

### Button

Uses shadcn/ui `Button` component with CVA variants. Standard heights:
- `xs`: 24px
- `sm`: 28px
- `default`: 32px
- `icon-xs`: 24x24
- `icon-sm`: 28x28

### Card

```
Background: bg-card
Border: border border-border
Radius: rounded-lg (6px)
Padding: p-3 or p-4
```

### Input

```
Height: 28px (sm) or 32px (default)
Background: bg-background
Border: border border-input
Radius: rounded-md (4px)
Focus: ring-2 ring-ring
Font: text-[13px] (monospace for code inputs)
```

### Badge

Uses shadcn/ui `Badge` component. Standard:
```
Height: auto (padding-based)
Padding: px-2 py-0.5
Font: text-[11px] font-medium
Radius: rounded-full
```

---

## Layout Patterns

### App Shell

```
+-- Sidebar (220px) --+-- Main Content (flex-1) ----+
|                      |                              |
|  Logo                |  <ErrorBanner />             |
|  Dashboard           |  <Page content />            |
|  Traces              |                              |
|  Playground          |                              |
|  Settings            |                              |
+----------------------+------------------------------+
```

- Sidebar: `w-[220px]` fixed, `h-screen`, `bg-sidebar`
- Main content: `flex-1 min-w-0 overflow-hidden`

### Three-Panel Debugger (Traces Page)

```
+-- TraceList --+-- TraceGraph ----------+-- SpanDetail --+
|   (280px)     |   (flex-1)             |   (380px)      |
|               |                        |                |
|   resizable ←→   CostSummaryBar       ←→  resizable    |
|               |   Graph                |                |
|               |   TimeTravel           |                |
+---------------+------------------------+----------------+
```

- Left panel: default 280px, resizable
- Center: flex-1, contains graph + controls
- Right panel: default 380px, resizable
- Resize handles: `w-1 cursor-col-resize`

---

## Animation & Transitions

| Speed | Duration | Usage |
|-------|----------|-------|
| Fast | `150ms` | Hover/active states, color changes |
| Normal | `200ms` | Layout changes, panel resizing |
| Slow | `300ms` | Page transitions, modals |

Use `transition-colors` for color-only changes, `transition-all` sparingly.

---

## Icons

- **Library:** Lucide React
- **Default size:** 14px for nav items, 12px for button icons, 16px for headers
- **Stroke width:** Default (2) — Lucide's standard
- **Color:** Inherit from parent text color (`currentColor`)

### Common Icons

| Icon | Import | Usage |
|------|--------|-------|
| `LayoutDashboard` | lucide-react | Dashboard nav |
| `Bug` | lucide-react | Traces/Debugger nav |
| `FlaskConical` | lucide-react | Playground nav |
| `Settings` | lucide-react | Settings nav |
| `KeyRound` | lucide-react | API keys |
| `Copy` | lucide-react | Copy-to-clipboard |
| `ExternalLink` | lucide-react | Open in new context |

---

## File Conventions

- UI primitives (shadcn): `frontend/src/components/ui/`
- Feature components: `frontend/src/components/<Feature>/`
- Pages: `frontend/src/pages/`
- State stores: `frontend/src/store/`
- Types: `frontend/src/lib/types.ts`
- API client: `frontend/src/lib/api.ts`
