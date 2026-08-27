import 'package:flutter/material.dart';
import '../theme/app_colors.dart';
import '../theme/app_typography.dart';

/// Section title with optional trailing widget.
/// Uses Work Sans, 18px, SemiBold, ALL CAPS with letter spacing per Stitch.
class SectionTitle extends StatelessWidget {
  final String title;
  final Widget? trailing;

  const SectionTitle({
    super.key,
    required this.title,
    this.trailing,
  });

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(
          title.toUpperCase(),
          style: AppTypography.sectionTitle.copyWith(
            color: AppColors.onSurfaceVariant,
          ),
        ),
        if (trailing != null) trailing!,
      ],
    );
  }
}
