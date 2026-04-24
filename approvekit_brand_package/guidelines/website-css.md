# ApproveKit Brand & Website Asset Guidelines

This folder contains cropped raster assets extracted from the supplied ApproveKit brand-board images. The original supplied boards are included in `reference/` for provenance.

## Package structure

```text
approvekit_brand_package/
  assets/
    favicon/
      favicon.ico
      favicon-16x16.png
      favicon-32x32.png
      favicon-48x48.png
      apple-touch-icon-180x180.png
      android-chrome-192x192.png
      android-chrome-512x512.png
      site.webmanifest
    icon/
      approvekit-icon.png
      approvekit-icon-64.png
      approvekit-icon-128.png
      approvekit-icon-192.png
      approvekit-icon-256.png
      approvekit-icon-512.png
      approvekit-icon-1024.png
    logo/
      approvekit-logo-light.png
      approvekit-logo-dark.png
      approvekit-logo-mono.png
      approvekit-logo-stacked.png
  css/
    approvekit.css
  guidelines/
    website-css.md
  reference/
    brand-assets.png
    web-usage.png
    design-guidelines.png
    website-guidelines.png
    css-tokens.png
```

## Which asset to use

| Use case | Asset |
| --- | --- |
| Main website navigation on light surfaces | `assets/logo/approvekit-logo-light.png` |
| Main website navigation on dark surfaces | `assets/logo/approvekit-logo-dark.png` |
| Compact UI spaces, favicon, app icon, social avatar | `assets/icon/approvekit-icon.png` |
| Single-color or print-adjacent usage | `assets/logo/approvekit-logo-mono.png` |
| Narrow centered lockups | `assets/logo/approvekit-logo-stacked.png` |

## Website head tags

```html
<link rel="icon" href="/assets/favicon/favicon.ico" sizes="any">
<link rel="icon" type="image/png" sizes="32x32" href="/assets/favicon/favicon-32x32.png">
<link rel="icon" type="image/png" sizes="16x16" href="/assets/favicon/favicon-16x16.png">
<link rel="apple-touch-icon" sizes="180x180" href="/assets/favicon/apple-touch-icon-180x180.png">
<link rel="manifest" href="/assets/favicon/site.webmanifest">
<meta name="theme-color" content="#2563EB">
```

## Logo usage example

```html
<nav class="ak-nav">
  <a href="/" aria-label="ApproveKit home">
    <img class="ak-logo ak-logo--lg ak-logo-light" src="/assets/logo/approvekit-logo-light.png" alt="ApproveKit">
    <img class="ak-logo ak-logo--lg ak-logo-dark" src="/assets/logo/approvekit-logo-dark.png" alt="ApproveKit">
  </a>
  <a class="ak-button ak-button--primary" href="/signup">Get Started</a>
</nav>
```

Apply `.theme-dark` or `data-theme="dark"` on `<html>` or `<body>` to switch token values and swap the logo.

```html
<body class="theme-dark">
  ...
</body>
```

## Color tokens

| Token | Hex |
| --- | --- |
| `--ak-blue` | `#2563EB` |
| `--ak-green` | `#22C55E` |
| `--ak-ink` | `#0F172A` |
| `--ak-slate` | `#64748B` |
| `--ak-fog` | `#F8FAFC` |
| `--ak-gray-200` | `#E5E7EB` |

## Theme tokens

### Light

```css
--ak-bg: #FFFFFF;
--ak-fg: #0F172A;
--ak-muted: #64748B;
--ak-card: #FFFFFF;
--ak-border: #E5E7EB;
--ak-ring: rgba(37, 99, 235, 0.25);
--ak-focus: #2563EB;
--ak-success: #22C55E;
--ak-danger: #EF4444;
--ak-warning: #F59E0B;
--ak-info: #2563EB;
```

### Dark

```css
--ak-bg: #0B1020;
--ak-fg: #F1F5F9;
--ak-muted: #94A3B8;
--ak-card: #111827;
--ak-border: #1F2937;
--ak-ring: rgba(37, 99, 235, 0.35);
--ak-focus: #60A5FA;
--ak-success: #22C55E;
--ak-danger: #F87171;
--ak-warning: #FBBF24;
--ak-info: #60A5FA;
```

## Sizing guidance

| Class | Use |
| --- | --- |
| `.ak-logo--sm` | Dense UI / small footer |
| `.ak-logo--md` | Compact nav |
| `.ak-logo--lg` | Default nav |
| `.ak-logo--xl` | Hero or marketing header |
| `.ak-icon--sm` | Small UI badges |
| `.ak-icon--md` | App navigation / cards |
| `.ak-icon--lg` | Hero mark / social preview |

Minimum recommended sizes:

- Horizontal logo: 120px wide / 24mm print.
- Icon-only mark: 24px wide / 6mm print.
- Favicon: keep mark clear at 16px and above.

## Clear space and cropping

- These exports are cropped to the visible logo/icon elements and saved as transparent PNG where appropriate.
- Keep at least `24px` or `1.5em` of padding around the logo in navs, footers, and cards.
- Do not place the logo on busy image backgrounds.
- Do not stretch, rotate, recolor, distort, add glows, or remove elements.
- Use SVG in the future when available; these exports are raster PNGs because the source material supplied here was raster screenshots.

## CSS

Import the bundled CSS:

```html
<link rel="stylesheet" href="/css/approvekit.css">
```

Or copy the tokens from `css/approvekit.css` into your design system.
