# WeatherGPT Design System

## Brand & Style
The design system is rooted in a "Warm Editorial" aesthetic, blending the precision of a high-end weather tool with the approachability of a lifestyle publication. The target audience includes discerning travelers, outdoor enthusiasts, and professionals who require high-confidence weather data presented with clarity and sophistication.

The style is characterized by **High-End Minimalism** and **Tactile Precision**. It avoids the sterile coldness of typical utility apps by using a warm, ivory-based palette and generous whitespace. The emotional response should be one of calm, intelligence, and reliability—mimicking the experience of reading a beautifully typeset weekend broadsheet or navigating a premium physical device.

## Colors
The palette is built upon a foundation of **Warm Ivory (#FAF8F3)**, providing a sophisticated alternative to pure white that reduces eye strain and feels more organic. 

- **Primary Text (#292724):** A deep, warm charcoal used for maximum legibility and authority.
- **Sunrise Amber (#E7A35A):** Used sparingly for key interactions, primary weather indicators, and moderate risk levels.
- **Soft Sky (#BFD8E3):** A muted, non-vibrant blue used for secondary surfaces and atmospheric contexts.
- **Risk Spectrum:** Semantic colors are desaturated to maintain a premium feel, ensuring "High" and "Severe" risks remain urgent without appearing "neon" or jarring.

**Color Palette Values:**
- `surface`: `#fbf9f4` (Warm Ivory)
- `surface-dim`: `#dbdad5`
- `surface-bright`: `#fbf9f4`
- `surface-container-lowest`: `#ffffff`
- `surface-container-low`: `#f5f3ee`
- `surface-container`: `#f0eee9`
- `surface-container-high`: `#eae8e3`
- `surface-container-highest`: `#e4e2dd`
- `on-surface`: `#1b1c19`
- `on-surface-variant`: `#4a463f`
- `inverse-surface`: `#30312e`
- `inverse-on-surface`: `#f2f1ec`
- `outline`: `#7b766f`
- `outline-variant`: `#ccc5bc`
- `surface-tint`: `#615e5a`
- `primary`: `#141310`
- `on-primary`: `#ffffff`
- `primary-container`: `#292724`
- `on-primary-container`: `#928e89`
- `inverse-primary`: `#cbc6c1`
- `secondary`: `#87520e`
- `on-secondary`: `#ffffff`
- `secondary-container`: `#ffb86d`
- `on-secondary-container`: `#794700`
- `tertiary`: `#00151c`
- `on-tertiary`: `#ffffff`
- `tertiary-container`: `#122a32`
- `on-tertiary-container`: `#7a929c`
- `error`: `#ba1a1a`
- `on-error`: `#ffffff`
- `error-container`: `#ffdad6`
- `on-error-container`: `#93000a`
- `background`: `#fbf9f4`
- `on-background`: `#1b1c19`

## Typography
The typography system uses **Plus Jakarta Sans** for headlines to achieve a modern, slightly soft sans-serif look that mimics SF Pro's friendliness, and **Work Sans** for body and labels to ensure professional grounding and exceptional legibility.

- **display-weather:** Plus Jakarta Sans, 84px, SemiBold (600), Line Height: 92px, Letter Spacing: -0.04em
- **headline-lg:** Plus Jakarta Sans, 32px, SemiBold (600), Line Height: 40px, Letter Spacing: -0.02em
- **headline-lg-mobile:** Plus Jakarta Sans, 24px, SemiBold (600), Line Height: 30px
- **section-title:** Work Sans, 18px, SemiBold (600), Line Height: 24px, Letter Spacing: 0.05em (All caps treatment recommended)
- **body-md:** Work Sans, 16px, Regular (400), Line Height: 26px
- **label-caps:** Work Sans, 12px, Medium (500), Line Height: 16px

Always prioritize vertical rhythm by aligning text to a 4px baseline grid.

## Layout & Spacing
The design system employs a **Fixed Content Width** on desktop and a **Fluid 4-Column Grid** on mobile.

- **Page Padding:** 24px margin on all mobile screens.
- **Gutters:** 16px between grid items.
- **Vertical Rhythm (Stacks):** 
  - `stack-sm`: 8px
  - `stack-md`: 16px
  - `stack-lg`: 32px
- **Section Margin:** 48px

## Elevation & Depth
Depth is created through **Tonal Layering** rather than heavy shadows. The background is `#FAF8F3`, while primary cards sit on `#FFFFFF`.

- **Soft Shadows:** Extremely diffused shadows for floating elements (e.g., input bar). Example: `0px 10px 30px rgba(41, 39, 36, 0.04)`.
- **Subtle Borders:** 1px solid border in `#F4DFC7` or `#E6F0F4` to define boundaries on secondary elements where shadows feel heavy.
- **Map Overlays:** "Muted Cream" or "Light Gray" map style. Overlays should be 95% opaque white cards with the standard 24px corner radius.

## Shapes & Corner Radii
The shape language is sophisticated and organic.

- **Cards:** Consistent 20px radius (`lg`: 1rem or slightly customized to 20px based on component).
- **Buttons & Inputs:** Interactive elements (search bar, scenario selectors) use a "Pill" shape (full radius / `9999px`).
- **Badges:** Risk indicators use a 6px radius (`sm`: 0.25rem ~ 4px, but explicitly 6px for badges).
- **Standard Scale:**
  - `sm`: 4px (0.25rem)
  - `DEFAULT`: 8px (0.5rem)
  - `md`: 12px (0.75rem)
  - `lg`: 16px (1rem)
  - `xl`: 24px (1.5rem)
  - `full`: 9999px

## Reusable Components
1. **Conversational Input:** Floating pill-shaped bar with soft `#FFFFFF` fill. Includes an elegant, amber-tinted microphone button on the right for voice interactions.
2. **Risk Badges:** Small capsules (6px radius) with light risk color tint (e.g., `#F4DFC7` for Moderate) and high-contrast text. Use a 2px colored dot for "Confidence Indicators."
3. **Scenario Sliders:** Minimalist tracks with circular `#FFFFFF` handle and `#E6F0F4` track color.
4. **Mode Selectors:** Segmented controls for Bike, Car, and Metro. Use subtle iconography (2pt stroke). Active state indicated by `#FFFFFF` raised tile.
5. **Tab Bar:** Minimalist footer with 4 icons. Background `#FAF8F3`, 1px top border (`#F4DFC7`). Active icons `#E7A35A`, inactive `#817B72`.
6. **Cards:** White (`#FFFFFF`) containers with 20px padding internally, 20px border radius. Title-heavy cards use `section-title` typography.
7. **Map View:** Muted style with 95% opaque overlay cards.
8. **Bottom Sheets:** Likely used for detailed analysis or hazard details over maps (implied by "Map Overlays" and typical mobile design patterns).

## Identified Screens
A total of 21 screens have been identified in the project:
1. WeatherGPT Home
2. WeatherGPT Home Refined
3. WeatherGPT Assistant
4. Local Hazard Details
5. Local Hazard Refined
6. Historical Replay
7. Historical Replay Refined
8. Risk & Confidence Summary
9. Risk & Confidence Refined
10. Mode Comparison
11. Mode Comparison Refined
12. Official Alert
13. Official Alert Refined
14. Trip Analysis
15. Trip Analysis Refined
16. What-If Simulator
17. What-If Simulator Refined
18. Alerts Feed
19. Alerts Feed Refined
20. Voice Input
21. Voice Input Refined

### Navigation Relationships
- **Home / Dashboard:** WeatherGPT Home / Home Refined
- **Primary AI Interaction:** WeatherGPT Assistant, Voice Input
- **Trip & Mode Context:** Trip Analysis, Mode Comparison, What-If Simulator
- **Risk & Alerting:** Alerts Feed, Official Alert, Risk & Confidence Summary, Local Hazard Details
- **Historical Analysis:** Historical Replay

## Inconsistencies / Discrepancies
- There are multiple versions of each screen (base version vs "Refined" version). We will likely need to align on whether to build the "Refined" versions primarily. The existence of these pairs suggests iterative design.
- The standard border radii are 0.25rem (4px) to 1.5rem (24px), but component specs explicitly call out 20px for cards and 6px for badges, requiring custom values in implementation overriding standard multiples of 4 or 8.
