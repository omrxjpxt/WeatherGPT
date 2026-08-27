import 'package:flutter/material.dart';
import '../theme/app_colors.dart';
import '../theme/tokens.dart';

/// Standard WeatherGPT card with soft shadow and 20px radius.
/// Matches the Stitch design: white background, warm shadow, 20px padding.
class WeatherCard extends StatelessWidget {
  final Widget child;
  final EdgeInsetsGeometry? padding;
  final Color? backgroundColor;
  final double? borderRadius;
  final Border? border;
  final VoidCallback? onTap;

  const WeatherCard({
    super.key,
    required this.child,
    this.padding,
    this.backgroundColor,
    this.borderRadius,
    this.border,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final card = Container(
      padding: padding ?? const EdgeInsets.all(Spacing.cardPadding),
      decoration: BoxDecoration(
        color: backgroundColor ?? AppColors.cardBackground,
        borderRadius: BorderRadius.circular(borderRadius ?? Radii.card),
        border: border,
        boxShadow: const [
          BoxShadow(
            offset: Offset(0, 10),
            blurRadius: 30,
            color: AppColors.softShadow,
          ),
        ],
      ),
      child: child,
    );

    if (onTap != null) {
      return GestureDetector(
        onTap: onTap,
        behavior: HitTestBehavior.opaque,
        child: card,
      );
    }
    return card;
  }
}
