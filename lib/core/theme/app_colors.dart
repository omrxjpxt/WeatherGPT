import 'package:flutter/material.dart';

/// WeatherGPT Design System Color Tokens
/// Source of Truth: Stitch Refined Screens + docs/DESIGN.md
class AppColors {
  AppColors._();

  // ── Brand Colors ──
  static const Color warmIvory = Color(0xFFFAF8F3);
  static const Color primaryText = Color(0xFF292724);
  static const Color sunriseAmber = Color(0xFFE7A35A);
  static const Color softSky = Color(0xFFBFD8E3);

  // ── Surface Hierarchy ──
  static const Color surface = Color(0xFFFBF9F4);
  static const Color surfaceDim = Color(0xFFDBDAD5);
  static const Color surfaceBright = Color(0xFFFBF9F4);
  static const Color surfaceContainerLowest = Color(0xFFFFFFFF);
  static const Color surfaceContainerLow = Color(0xFFF5F3EE);
  static const Color surfaceContainer = Color(0xFFF0EEE9);
  static const Color surfaceContainerHigh = Color(0xFFEAE8E3);
  static const Color surfaceContainerHighest = Color(0xFFE4E2DD);

  // ── On Surface ──
  static const Color onSurface = Color(0xFF1B1C19);
  static const Color onSurfaceVariant = Color(0xFF4A463F);

  // ── Inverse ──
  static const Color inverseSurface = Color(0xFF30312E);
  static const Color inverseOnSurface = Color(0xFFF2F1EC);

  // ── Outline ──
  static const Color outline = Color(0xFF7B766F);
  static const Color outlineVariant = Color(0xFFCCC5BC);

  // ── Primary ──
  static const Color primary = Color(0xFF141310);
  static const Color onPrimary = Color(0xFFFFFFFF);
  static const Color primaryContainer = Color(0xFF292724);
  static const Color onPrimaryContainer = Color(0xFF928E89);

  // ── Secondary ──
  static const Color secondary = Color(0xFF87520E);
  static const Color onSecondary = Color(0xFFFFFFFF);
  static const Color secondaryContainer = Color(0xFFFFB86D);
  static const Color onSecondaryContainer = Color(0xFF794700);

  // ── Tertiary ──
  static const Color tertiary = Color(0xFF00151C);
  static const Color onTertiary = Color(0xFFFFFFFF);
  static const Color tertiaryContainer = Color(0xFF122A32);
  static const Color onTertiaryContainer = Color(0xFF7A929C);

  // ── Error ──
  static const Color error = Color(0xFFBA1A1A);
  static const Color onError = Color(0xFFFFFFFF);
  static const Color errorContainer = Color(0xFFFFDAD6);
  static const Color onErrorContainer = Color(0xFF93000A);

  // ── Borders & Separators ──
  static const Color cardBorderWarm = Color(0xFFF4DFC7);
  static const Color cardBorderCool = Color(0xFFE6F0F4);
  static const Color tabBarBorder = Color(0xFFF4DFC7);

  // ── Tab Bar Icons ──
  static const Color tabActive = sunriseAmber;
  static const Color tabInactive = Color(0xFF817B72);

  // ── Scenario Slider ──
  static const Color sliderTrack = Color(0xFFE6F0F4);
  static const Color sliderThumb = Color(0xFFFFFFFF);

  // ── Risk Spectrum ──
  static const Color riskLow = Color(0xFF4CAF50);
  static const Color riskLowBg = Color(0xFFE8F5E9);
  static const Color riskModerate = sunriseAmber;
  static const Color riskModerateBg = Color(0xFFF4DFC7);
  static const Color riskHigh = Color(0xFFE57C23);
  static const Color riskHighBg = Color(0xFFFFF3E0);
  static const Color riskSevere = Color(0xFFD32F2F);
  static const Color riskSevereBg = Color(0xFFFFEBEE);

  // ── Card ──
  static const Color cardBackground = Color(0xFFFFFFFF);

  // ── Shadows ──
  static const Color softShadow = Color(0x0A292724); // rgba(41,39,36,0.04)
}
