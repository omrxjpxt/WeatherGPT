import 'package:flutter/material.dart';
import 'app_colors.dart';
import 'app_typography.dart';
import 'tokens.dart';

export 'app_colors.dart';
export 'app_typography.dart';
export 'tokens.dart';

/// Builds the WeatherGPT Material ThemeData
/// Warm Editorial aesthetic with Ivory-based palette
class AppTheme {
  AppTheme._();

  static ThemeData get light {
    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.light,
      scaffoldBackgroundColor: AppColors.warmIvory,
      colorScheme: const ColorScheme.light(
        surface: AppColors.surface,
        onSurface: AppColors.onSurface,
        surfaceContainerLowest: AppColors.surfaceContainerLowest,
        surfaceContainerLow: AppColors.surfaceContainerLow,
        surfaceContainer: AppColors.surfaceContainer,
        surfaceContainerHigh: AppColors.surfaceContainerHigh,
        surfaceContainerHighest: AppColors.surfaceContainerHighest,
        primary: AppColors.primary,
        onPrimary: AppColors.onPrimary,
        primaryContainer: AppColors.primaryContainer,
        onPrimaryContainer: AppColors.onPrimaryContainer,
        secondary: AppColors.secondary,
        onSecondary: AppColors.onSecondary,
        secondaryContainer: AppColors.secondaryContainer,
        onSecondaryContainer: AppColors.onSecondaryContainer,
        tertiary: AppColors.tertiary,
        onTertiary: AppColors.onTertiary,
        tertiaryContainer: AppColors.tertiaryContainer,
        onTertiaryContainer: AppColors.onTertiaryContainer,
        error: AppColors.error,
        onError: AppColors.onError,
        errorContainer: AppColors.errorContainer,
        onErrorContainer: AppColors.onErrorContainer,
        outline: AppColors.outline,
        outlineVariant: AppColors.outlineVariant,
        inverseSurface: AppColors.inverseSurface,
        onInverseSurface: AppColors.inverseOnSurface,
      ),

      // ── Typography ──
      fontFamily: 'WorkSans',
      textTheme: const TextTheme(
        displayLarge: AppTypography.displayWeather,
        headlineLarge: AppTypography.headlineLg,
        headlineMedium: AppTypography.headlineLgMobile,
        headlineSmall: AppTypography.headlineMd,
        titleLarge: AppTypography.sectionTitle,
        bodyLarge: AppTypography.bodyMd,
        bodyMedium: AppTypography.bodySm,
        labelLarge: AppTypography.buttonLabel,
        labelMedium: AppTypography.labelMd,
        labelSmall: AppTypography.labelCaps,
      ),

      // ── AppBar ──
      appBarTheme: const AppBarTheme(
        backgroundColor: AppColors.warmIvory,
        surfaceTintColor: Colors.transparent,
        elevation: 0,
        centerTitle: false,
        titleTextStyle: TextStyle(
          fontFamily: 'PlusJakartaSans',
          fontSize: 20,
          fontWeight: FontWeight.w600,
          color: AppColors.primaryText,
          height: 26 / 20,
        ),
        iconTheme: IconThemeData(color: AppColors.primaryText),
      ),

      // ── Cards ──
      cardTheme: CardThemeData(
        color: AppColors.cardBackground,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(Radii.card),
        ),
        margin: EdgeInsets.zero,
      ),

      // ── Bottom Navigation ──
      bottomNavigationBarTheme: const BottomNavigationBarThemeData(
        backgroundColor: AppColors.warmIvory,
        selectedItemColor: AppColors.tabActive,
        unselectedItemColor: AppColors.tabInactive,
        type: BottomNavigationBarType.fixed,
        elevation: 0,
        selectedLabelStyle: AppTypography.labelCaps,
        unselectedLabelStyle: AppTypography.labelCaps,
      ),

      // ── Divider ──
      dividerTheme: const DividerThemeData(
        color: AppColors.cardBorderWarm,
        thickness: 1,
        space: 0,
      ),
    );
  }
}
