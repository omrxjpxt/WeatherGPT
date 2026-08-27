import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';
import '../theme/app_colors.dart';
import '../theme/app_typography.dart';
import '../theme/tokens.dart';

/// Floating pill-shaped conversational input bar per Stitch design.
/// White fill, soft shadow, amber microphone button on the right.
class ConversationalInputBar extends StatelessWidget {
  final VoidCallback? onTap;
  final VoidCallback? onMicTap;
  final String hintText;

  const ConversationalInputBar({
    super.key,
    this.onTap,
    this.onMicTap,
    this.hintText = 'Ask WeatherGPT anything...',
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
        decoration: BoxDecoration(
          color: AppColors.cardBackground,
          borderRadius: BorderRadius.circular(Radii.full),
          boxShadow: const [
            BoxShadow(
              offset: Offset(0, 10),
              blurRadius: 30,
              color: AppColors.softShadow,
            ),
          ],
        ),
        child: Row(
          children: [
            Icon(
              CupertinoIcons.search,
              color: AppColors.onSurfaceVariant,
              size: 20,
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Text(
                hintText,
                style: AppTypography.bodyMd.copyWith(
                  color: AppColors.outline,
                ),
              ),
            ),
            GestureDetector(
              onTap: onMicTap,
              child: Container(
                width: 36,
                height: 36,
                decoration: BoxDecoration(
                  color: AppColors.sunriseAmber,
                  shape: BoxShape.circle,
                ),
                child: const Icon(
                  CupertinoIcons.mic_fill,
                  color: Colors.white,
                  size: 18,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
