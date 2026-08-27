import 'package:flutter/material.dart';
import '../../models/models.dart';
import '../theme/app_colors.dart';
import '../theme/app_typography.dart';
import '../theme/tokens.dart';

/// Risk badge matching Stitch design:
/// Small capsule with 6px radius, light tinted background, high-contrast text.
class RiskBadge extends StatelessWidget {
  final RiskLevel level;
  final String? label;
  final bool showDot;

  const RiskBadge({
    super.key,
    required this.level,
    this.label,
    this.showDot = true,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: _backgroundColor,
        borderRadius: BorderRadius.circular(Radii.badge),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (showDot) ...[
            Container(
              width: 6,
              height: 6,
              decoration: BoxDecoration(
                color: _dotColor,
                shape: BoxShape.circle,
              ),
            ),
            const SizedBox(width: 6),
          ],
          Text(
            label ?? _defaultLabel,
            style: AppTypography.labelCaps.copyWith(
              color: _textColor,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }

  String get _defaultLabel => switch (level) {
    RiskLevel.low => 'LOW',
    RiskLevel.moderate => 'MODERATE',
    RiskLevel.high => 'HIGH',
    RiskLevel.severe => 'SEVERE',
  };

  Color get _backgroundColor => switch (level) {
    RiskLevel.low => AppColors.riskLowBg,
    RiskLevel.moderate => AppColors.riskModerateBg,
    RiskLevel.high => AppColors.riskHighBg,
    RiskLevel.severe => AppColors.riskSevereBg,
  };

  Color get _dotColor => switch (level) {
    RiskLevel.low => AppColors.riskLow,
    RiskLevel.moderate => AppColors.riskModerate,
    RiskLevel.high => AppColors.riskHigh,
    RiskLevel.severe => AppColors.riskSevere,
  };

  Color get _textColor => switch (level) {
    RiskLevel.low => const Color(0xFF2E7D32),
    RiskLevel.moderate => const Color(0xFF8B5E00),
    RiskLevel.high => const Color(0xFFBF360C),
    RiskLevel.severe => const Color(0xFFB71C1C),
  };
}

/// Circular risk score display with colored ring
class RiskScoreIndicator extends StatelessWidget {
  final int score;
  final RiskLevel level;
  final double size;

  const RiskScoreIndicator({
    super.key,
    required this.score,
    required this.level,
    this.size = 100,
  });

  @override
  Widget build(BuildContext context) {
    final color = switch (level) {
      RiskLevel.low => AppColors.riskLow,
      RiskLevel.moderate => AppColors.riskModerate,
      RiskLevel.high => AppColors.riskHigh,
      RiskLevel.severe => AppColors.riskSevere,
    };

    return SizedBox(
      width: size,
      height: size,
      child: Stack(
        alignment: Alignment.center,
        children: [
          SizedBox(
            width: size,
            height: size,
            child: CircularProgressIndicator(
              value: score / 100,
              strokeWidth: 6,
              backgroundColor: AppColors.surfaceContainerHigh,
              valueColor: AlwaysStoppedAnimation<Color>(color),
              strokeCap: StrokeCap.round,
            ),
          ),
          Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                '$score',
                style: AppTypography.headlineLgMobile.copyWith(
                  color: AppColors.primaryText,
                  fontWeight: FontWeight.w700,
                ),
              ),
              Text(
                '/ 100',
                style: AppTypography.labelCaps.copyWith(
                  color: AppColors.onSurfaceVariant,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
