---
name: frontend-design
description: Guidelines and best practices for creating a stunning, responsive, dark-themed dashboard for football analytics with glassmorphism and modern visual design language.
---

# Frontend Design Guidelines & Design System

This skill outlines guidelines for styling and design execution for the BallMetrix web dashboard.

## Color Palette (Premium Dark Mode)
- **Primary Background**: HSL(220, 20%, 6%) to HSL(220, 20%, 10%) - very dark blue-grey.
- **Surface (Card) Background**: HSL(220, 15%, 13%) with 60% opacity for glassmorphism.
- **Primary Accent**: HSL(142, 70%, 45%) - vibrant pitch green for match data and positive indicators.
- **Secondary Accent**: HSL(200, 90%, 50%) - electric cyan for prediction meters and probability tracks.
- **Warning/Alert**: HSL(15, 90%, 55%) - warm orange for upset meters and risk metrics.
- **Text**: Primary `#FFFFFF` (90% opacity), Secondary `#94A3B8` (muted grey).

## Glassmorphism (CSS)
Apply to all card containers:
```css
.card {
  background: rgba(26, 32, 44, 0.6);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
}
```

## Typography
- Use `Outfit` or `Inter` from Google Fonts.
- Header weight: `700` (Bold) or `800` (Extra Bold) for numbers.
- Body weight: `400` (Regular) and `500` (Medium).

## Interaction & Animations
- Use Framer Motion for React transitions.
- Hover animations on interactive cards: subtle lift (`translateY(-4px)`) and increase border-color opacity.
- Pulse animations for live data indicators.
- Smooth loading sequences with skeleton screens instead of plain spinners.
