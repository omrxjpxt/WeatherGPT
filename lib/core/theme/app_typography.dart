import 'package:flutter/material.dart';

/// WeatherGPT Typography System
/// Source of Truth: Stitch Design System
///
/// Headlines: Plus Jakarta Sans
/// Body & Labels: Work Sans
class AppTypography {
  AppTypography._();

  static const String _headlineFont = 'PlusJakartaSans';
  static const String _bodyFont = 'WorkSans';

  /// 84px / 92px, SemiBold, -0.04em — Temperature display
  static const TextStyle displayWeather = TextStyle(
    fontFamily: _headlineFont,
    fontSize: 84,
    fontWeight: FontWeight.w600,
    height: 92 / 84,
    letterSpacing: -0.04 * 84, // -3.36px
  );

  /// 32px / 40px, SemiBold, -0.02em — Large headlines
  static const TextStyle headlineLg = TextStyle(
    fontFamily: _headlineFont,
    fontSize: 32,
    fontWeight: FontWeight.w600,
    height: 40 / 32,
    letterSpacing: -0.02 * 32, // -0.64px
  );

  /// 24px / 30px, SemiBold — Mobile headlines
  static const TextStyle headlineLgMobile = TextStyle(
    fontFamily: _headlineFont,
    fontSize: 24,
    fontWeight: FontWeight.w600,
    height: 30 / 24,
  );

  /// 20px / 26px, SemiBold — Card titles
  static const TextStyle headlineMd = TextStyle(
    fontFamily: _headlineFont,
    fontSize: 20,
    fontWeight: FontWeight.w600,
    height: 26 / 20,
  );

  /// 18px / 24px, SemiBold, 0.05em — Section titles (ALL CAPS)
  static const TextStyle sectionTitle = TextStyle(
    fontFamily: _bodyFont,
    fontSize: 18,
    fontWeight: FontWeight.w600,
    height: 24 / 18,
    letterSpacing: 0.05 * 18, // 0.9px
  );

  /// 16px / 26px, Regular — Body text
  static const TextStyle bodyMd = TextStyle(
    fontFamily: _bodyFont,
    fontSize: 16,
    fontWeight: FontWeight.w400,
    height: 26 / 16,
  );

  /// 14px / 22px, Regular — Secondary body
  static const TextStyle bodySm = TextStyle(
    fontFamily: _bodyFont,
    fontSize: 14,
    fontWeight: FontWeight.w400,
    height: 22 / 14,
  );

  /// 12px / 16px, Medium — Label text (ALL CAPS)
  static const TextStyle labelCaps = TextStyle(
    fontFamily: _bodyFont,
    fontSize: 12,
    fontWeight: FontWeight.w500,
    height: 16 / 12,
  );

  /// 14px / 20px, Medium — Label for interactive elements
  static const TextStyle labelMd = TextStyle(
    fontFamily: _bodyFont,
    fontSize: 14,
    fontWeight: FontWeight.w500,
    height: 20 / 14,
  );

  /// 16px / 24px, SemiBold — Button labels
  static const TextStyle buttonLabel = TextStyle(
    fontFamily: _bodyFont,
    fontSize: 16,
    fontWeight: FontWeight.w600,
    height: 24 / 16,
  );

  /// 48px / 56px, SemiBold — Large risk score display
  static const TextStyle displayScore = TextStyle(
    fontFamily: _headlineFont,
    fontSize: 48,
    fontWeight: FontWeight.w600,
    height: 56 / 48,
    letterSpacing: -0.02 * 48,
  );
}
