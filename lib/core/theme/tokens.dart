/// WeatherGPT Spacing, Radius, and Elevation Tokens
/// Source of Truth: Stitch Design System
class Spacing {
  Spacing._();

  static const double xs = 4;
  static const double sm = 8;
  static const double md = 16;
  static const double lg = 24;
  static const double xl = 32;
  static const double xxl = 48;

  // ── Named Tokens ──
  static const double pagePadding = 24;
  static const double gutter = 16;
  static const double stackSm = 8;
  static const double stackMd = 16;
  static const double stackLg = 32;
  static const double sectionMargin = 48;
  static const double cardPadding = 20;
}

class Radii {
  Radii._();

  static const double sm = 4;     // 0.25rem
  static const double base = 8;   // 0.5rem
  static const double md = 12;    // 0.75rem
  static const double lg = 16;    // 1rem
  static const double xl = 24;    // 1.5rem
  static const double card = 20;  // Cards per design
  static const double badge = 6;  // Risk badge
  static const double full = 9999; // Pill shape
}

class Elevation {
  Elevation._();

  /// Soft diffused shadow for floating elements
  /// 0px 10px 30px rgba(41, 39, 36, 0.04)
  static const List<BoxShadowData> softShadow = [
    BoxShadowData(
      offsetX: 0,
      offsetY: 10,
      blurRadius: 30,
      color: 0x0A292724,
    ),
  ];
}

/// Helper class to hold box shadow data without importing material
class BoxShadowData {
  final double offsetX;
  final double offsetY;
  final double blurRadius;
  final int color;

  const BoxShadowData({
    required this.offsetX,
    required this.offsetY,
    required this.blurRadius,
    required this.color,
  });
}
