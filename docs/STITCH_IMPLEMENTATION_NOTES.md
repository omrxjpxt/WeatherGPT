# Stitch Implementation Notes (Flutter)

## Stitch Screen → Flutter Screen Mapping
Based on the extracted Stitch project, here is the initial mapping of the 21 identified screens to Flutter widgets/routes:

- **WeatherGPT Home / Home Refined** -> `HomeScreen` (`/home`)
- **WeatherGPT Assistant** -> `AssistantScreen` (`/assistant`)
- **Voice Input / Voice Input Refined** -> `VoiceInputModal` (Bottom Sheet or Overlay on `/assistant`)
- **Alerts Feed / Alerts Feed Refined** -> `AlertsFeedScreen` (`/alerts`)
- **Official Alert / Official Alert Refined** -> `AlertDetailScreen` (`/alerts/detail`)
- **Local Hazard Details / Local Hazard Refined** -> `LocalHazardScreen` (`/hazard`)
- **Risk & Confidence Summary / Risk & Confidence Refined** -> `RiskSummaryScreen` (`/risk`)
- **Trip Analysis / Trip Analysis Refined** -> `TripAnalysisScreen` (`/trip`)
- **Mode Comparison / Mode Comparison Refined** -> `ModeComparisonScreen` (`/trip/compare`)
- **What-If Simulator / What-If Simulator Refined** -> `SimulatorScreen` (`/simulator`)
- **Historical Replay / Historical Replay Refined** -> `HistoricalReplayScreen` (`/history`)

*(Note: We should clarify with the user if we are implementing the "Refined" versions exclusively, which is highly likely).*

## Reusable Flutter Widgets Required
To maintain consistency and development speed, the following reusable Flutter widgets must be created based on the design system:

1. **`WeatherScaffold`**: A custom scaffold with a `#FAF8F3` (Warm Ivory) background, handling safe areas, and containing the custom `BottomNavigationBar`.
2. **`WeatherCard`**: A container widget with `#FFFFFF` background, 20px border radius, 20px internal padding, and the specific soft shadow (`0px 10px 30px rgba(41, 39, 36, 0.04)`).
3. **`SectionTitle`**: A Text widget preset to `Work Sans`, 18px, SemiBold, All Caps with letter spacing.
4. **`RiskBadge`**: A capsule widget (6px radius) taking a Risk Level enum to determine its background tint and dot color.
5. **`ConversationalInputBar`**: A pill-shaped (full radius) floating input field with the Sunrise Amber microphone button.
6. **`ModeSelector`**: A segmented control widget with an animated `#FFFFFF` raised tile for the active state.
7. **`ScenarioSlider`**: A custom `Slider` widget with a `#E6F0F4` track and a white circular thumb.
8. **`MapOverlayCard`**: A variant of `WeatherCard` with 95% opacity.

## Important Layout Constraints
- **Vertical Rhythm**: UI spacing must strictly adhere to the 8px/16px/32px scale. Flutter's `SizedBox(height: ...)` will be heavily used.
- **Card Padding**: Every standard data card requires exactly `EdgeInsets.all(20.0)`.
- **Typography Baseline**: Custom text heights should be used to align to a 4px baseline grid.

## Responsive Behavior
- The Stitch design specifies a **Fluid 4-Column Grid** on mobile and a **Fixed Content Width** on desktop (max 1200px).
- In Flutter, we will use `LayoutBuilder` and `ConstrainedBox` (maxWidth: 1200) at the root of the body.
- On larger screens (web/tablet), the UI should transition from single-column scroll to a multi-pane layout (Map on left, AI Insights on right).

## iPhone Safe-Area Requirements
- The "Warm Editorial" aesthetic heavily relies on generous whitespace.
- `SafeArea` must be used to prevent content from bleeding under the Dynamic Island/Notch or the bottom home indicator.
- The `ConversationalInputBar` and the minimalist Tab Bar must account for the bottom safe area inset.
- Mobile screens require a strict 24px horizontal padding (`EdgeInsets.symmetric(horizontal: 24.0)`).

## Implementation Challenges in Flutter
1. **Custom Soft Shadows**: Flutter's default `BoxShadow` can sometimes render slightly harsher than web/Figma shadows. We need to carefully tune the `blurRadius` (approx 30) and `spreadRadius` (approx 0) with a very low opacity color (`Color(0x0A292724)`).
2. **Blur / Glassmorphism**: If the map overlay requires a blur effect behind the 95% opacity, we will need to use `BackdropFilter` with `ImageFilter.blur`, which can have performance implications on older devices if overused during scroll.
3. **Typography Fonts**: Both `Plus Jakarta Sans` and `Work Sans` need to be explicitly added to `pubspec.yaml` via Google Fonts or bundled assets. `Plus Jakarta Sans` letter spacing adjustments (`-0.04em`, `-0.02em`) must be calculated accurately in Flutter's `letterSpacing` property (which uses logical pixels).

## Ambiguities & Open Questions
1. **Refined vs Standard Screens**: The project contains pairs of screens (e.g., `Voice Input` and `Voice Input Refined`). We assume the "Refined" versions are the final target, but need confirmation.
2. **Bottom Navigation**: The design specifies a tab bar, but many of the identified screens (What-If Simulator, Historical Replay) don't naturally fit into a standard 4-tab structure. We need to define the exact routing map and which screens are top-level tabs vs pushed routes.
3. **Map Provider**: The map design dictates a "Muted Cream" or "Light Gray" style. We will need to know if we are using Google Maps with a custom JSON style, or Mapbox, to achieve this specific look.
