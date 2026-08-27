import 'package:flutter/material.dart';
import '../../models/models.dart';
import '../theme/app_colors.dart';
import '../theme/app_typography.dart';
import '../theme/tokens.dart';

/// Mode selector: Segmented control for Bike/Car/Metro
/// Active state: white raised tile. Inactive: transparent.
class ModeSelector extends StatelessWidget {
  final TransportMode selected;
  final ValueChanged<TransportMode> onChanged;

  const ModeSelector({
    super.key,
    required this.selected,
    required this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(4),
      decoration: BoxDecoration(
        color: AppColors.surfaceContainerHigh,
        borderRadius: BorderRadius.circular(Radii.xl),
      ),
      child: Row(
        children: TransportMode.values
            .where((m) => m != TransportMode.walk)
            .map((mode) => Expanded(
                  child: _ModeTab(
                    mode: mode,
                    isSelected: selected == mode,
                    onTap: () => onChanged(mode),
                  ),
                ))
            .toList(),
      ),
    );
  }
}

class _ModeTab extends StatelessWidget {
  final TransportMode mode;
  final bool isSelected;
  final VoidCallback onTap;

  const _ModeTab({
    required this.mode,
    required this.isSelected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        curve: Curves.easeInOut,
        padding: const EdgeInsets.symmetric(vertical: 10),
        decoration: BoxDecoration(
          color: isSelected ? AppColors.cardBackground : Colors.transparent,
          borderRadius: BorderRadius.circular(Radii.xl - 4),
          boxShadow: isSelected
              ? const [
                  BoxShadow(
                    offset: Offset(0, 2),
                    blurRadius: 8,
                    color: AppColors.softShadow,
                  ),
                ]
              : null,
        ),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              _iconForMode(mode),
              size: 18,
              color: isSelected
                  ? AppColors.primaryText
                  : AppColors.onSurfaceVariant,
            ),
            const SizedBox(width: 6),
            Text(
              _labelForMode(mode),
              style: AppTypography.labelMd.copyWith(
                color: isSelected
                    ? AppColors.primaryText
                    : AppColors.onSurfaceVariant,
                fontWeight: isSelected ? FontWeight.w600 : FontWeight.w500,
              ),
            ),
          ],
        ),
      ),
    );
  }

  IconData _iconForMode(TransportMode mode) => switch (mode) {
        TransportMode.bike => Icons.two_wheeler,
        TransportMode.car => Icons.directions_car_outlined,
        TransportMode.metro => Icons.train_outlined,
        TransportMode.walk => Icons.directions_walk,
      };

  String _labelForMode(TransportMode mode) => switch (mode) {
        TransportMode.bike => 'Bike',
        TransportMode.car => 'Car',
        TransportMode.metro => 'Metro',
        TransportMode.walk => 'Walk',
      };
}
