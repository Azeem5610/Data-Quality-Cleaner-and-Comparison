# Data Quality Cleaner — Design System

## Product context

An analyst-facing workspace that cleans noisy PDFs and web pages, explains what was removed, and compares retrieval answers from the original and cleaned text. The single-page workflow should feel clear, trustworthy, and precise for technical and non-technical demo users.

## Visual direction

- Build a calm, editorial data workspace with a warm light canvas and a restrained deep forest accent.
- Avoid gradient-heavy backgrounds, oversized marketing typography, glass effects, excessive pills, and decorative dashboard filler.
- Use strong hierarchy, compact labels, clear panel boundaries, and generous whitespace around the main comparison.
- Keep data and source text legible. Use category color only to explain removals.

## Color tokens

| Token | Value | Use |
| --- | --- | --- |
| `--canvas` | `#F5F5F1` | App background |
| `--surface` | `#FFFFFF` | Main cards and panels |
| `--surface-muted` | `#F0F1EC` | Secondary panels and inset areas |
| `--ink` | `#202923` | Primary text |
| `--ink-muted` | `#667168` | Supporting text |
| `--line` | `#DDE2DB` | Borders and dividers |
| `--forest` | `#245B45` | Primary action and active state |
| `--forest-dark` | `#193F31` | Hover and strong accent |
| `--forest-soft` | `#E5F0E9` | Subtle accent surfaces |
| `--amber` | `#B87518` | Attention / whitespace and boilerplate removals |
| `--red` | `#B44D46` | Cookie and consent removals |
| `--blue` | `#4A7195` | Navigation removals |
| `--violet` | `#7563A6` | Duplicate removals |
| `--slate` | `#738078` | Header/footer and page-number removals |

## Typography

- Use `Inter` when available, with `ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif` fallback.
- Page title: 26–30px, 650–700 weight, tight line-height.
- Section title: 15–17px, 620–680 weight.
- Body: 14–15px, 400–500 weight, line-height 1.55.
- Metadata and labels: 11–12px, 550–650 weight, modest tracking.
- Use a tabular numeral style for percentages and counts.
- Source text can use a readable system sans; monospace is reserved for IDs and technical offsets.

## Shape, spacing, depth

- Base spacing rhythm: 4, 8, 12, 16, 24, 32px.
- Card radius: 12px; input and button radius: 8px; compact badges: 6px.
- Borders are preferred over shadows. Use only a soft `0 8px 24px rgba(32, 41, 35, 0.06)` shadow for lifted menus or dialogs.
- Main content width: fluid, with a comfortable maximum near 1440px.
- Desktop page gutters: 36–48px; tablet: 24px; mobile: 16px.

## Interaction and responsive behavior

- Primary actions use forest green with clear hover, focus, disabled, and loading states.
- All controls have visible keyboard focus and accessible labels.
- Report categories have persistent text labels in addition to color.
- On narrow screens, stack the raw/clean panels and answer cards vertically; preserve source labels and remove horizontal overflow.
- Respect `prefers-reduced-motion`; use short transitions only for state changes.
