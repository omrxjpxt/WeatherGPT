import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_typography.dart';
import '../../core/theme/tokens.dart';
import '../../core/widgets/widgets.dart';
import '../../core/providers.dart';
import '../../models/models.dart';

/// Mode Comparison Refined — Switch between Bike/Car/Metro
class ModeComparisonScreen extends ConsumerStatefulWidget {
  const ModeComparisonScreen({super.key});

  @override
  ConsumerState<ModeComparisonScreen> createState() => _ModeComparisonState();
}

class _ModeComparisonState extends ConsumerState<ModeComparisonScreen> {
  TransportMode _selected = TransportMode.bike;

  @override
  Widget build(BuildContext context) {
    final modesAsync = ref.watch(modeComparisonProvider);

    return Scaffold(
      backgroundColor: AppColors.warmIvory,
      appBar: AppBar(
        leading: IconButton(
          icon: const Icon(CupertinoIcons.back),
          onPressed: () => context.pop(),
        ),
        title: const Text('Compare Modes'),
      ),
      body: modesAsync.when(
        data: (modes) {
          final current = modes.firstWhere((m) => m.mode == _selected);
          return SingleChildScrollView(
            padding: const EdgeInsets.symmetric(horizontal: Spacing.pagePadding),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const SizedBox(height: Spacing.stackMd),

                // ── Mode Selector ──
                ModeSelector(
                  selected: _selected,
                  onChanged: (mode) => setState(() => _selected = mode),
                ),
                const SizedBox(height: Spacing.stackLg),

                // ── Selected Mode Stats ──
                AnimatedSwitcher(
                  duration: const Duration(milliseconds: 300),
                  child: WeatherCard(
                    key: ValueKey(_selected),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Icon(_iconForMode(_selected),
                                color: AppColors.primaryText, size: 28),
                            const SizedBox(width: 12),
                            Text(
                              _labelForMode(_selected),
                              style: AppTypography.headlineMd.copyWith(
                                color: AppColors.primaryText,
                              ),
                            ),
                            const Spacer(),
                           if (current.risk != null)
                            RiskBadge(level: current.risk!.level),
                          ],
                        ),
                        const SizedBox(height: Spacing.stackMd),

                        // Stats row
                        Row(
                          children: [
                            _StatItem(
                              label: 'ETA',
                              value: '${current.estimatedDuration.inMinutes} min',
                            ),
                          if (current.risk != null)
                            _StatItem(
                              label: 'Risk',
                              value: '${current.risk!.overallScore}/100',
                            ),
                            _StatItem(
                              label: 'Distance',
                              value: '${current.distanceKm} km',
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: Spacing.stackLg),

                // ── Risk Comparison ──
                const SectionTitle(title: 'Risk Comparison'),
                const SizedBox(height: Spacing.stackMd),
                ...modes.map((m) => _buildModeComparisonRow(m)),
                const SizedBox(height: Spacing.stackLg),

                // ── Highlights ──
                AnimatedSwitcher(
                  duration: const Duration(milliseconds: 300),
                  child: Column(
                    key: ValueKey(_selected),
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const SectionTitle(title: 'Key Points'),
                      const SizedBox(height: Spacing.stackSm),
                      ...current.highlights.map((h) => _buildHighlightRow(h)),
                    ],
                  ),
                ),
                const SizedBox(height: Spacing.stackLg),

                // ── Recommendation ──
                if (current.recommendation != null)
                  WeatherCard(
                    backgroundColor: AppColors.surfaceContainerLow,
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Icon(CupertinoIcons.lightbulb,
                            color: AppColors.sunriseAmber, size: 18),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Text(
                            current.recommendation!,
                            style: AppTypography.bodySm.copyWith(
                              color: AppColors.primaryText,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                const SizedBox(height: Spacing.sectionMargin),
              ],
            ),
          );
        },
        loading: () => const Center(
          child: CircularProgressIndicator(color: AppColors.sunriseAmber),
        ),
        error: (e, _) => Center(child: Text('Error: $e')),
      ),
    );
  }

  Widget _buildModeComparisonRow(ModeOption mode) {
    final isActive = mode.mode == _selected;
    final color = mode.risk != null ? _colorForRisk(mode.risk!.level) : AppColors.outline;
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: GestureDetector(
        onTap: () => setState(() => _selected = mode.mode),
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 200),
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: isActive ? AppColors.cardBackground : AppColors.surfaceContainerLow,
            borderRadius: BorderRadius.circular(Radii.card),
            border: isActive ? Border.all(color: AppColors.sunriseAmber, width: 2) : null,
            boxShadow: isActive
                ? const [BoxShadow(offset: Offset(0, 4), blurRadius: 12, color: AppColors.softShadow)]
                : null,
          ),
          child: Row(
            children: [
              Icon(_iconForMode(mode.mode), size: 24,
                  color: isActive ? AppColors.primaryText : AppColors.onSurfaceVariant),
              const SizedBox(width: 12),
              Expanded(
                child: Text(
                  _labelForMode(mode.mode),
                  style: AppTypography.labelMd.copyWith(
                    color: isActive ? AppColors.primaryText : AppColors.onSurfaceVariant,
                    fontWeight: isActive ? FontWeight.w600 : FontWeight.w500,
                  ),
                ),
              ),
              Text(
                '${mode.estimatedDuration.inMinutes} min',
                style: AppTypography.bodySm.copyWith(
                  color: AppColors.onSurfaceVariant,
                ),
              ),
              const SizedBox(width: 12),
              // Risk bar
              SizedBox(
                width: 60,
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(4),
                  child: mode.risk != null
                    ? LinearProgressIndicator(
                        value: mode.risk!.overallScore / 100,
                        backgroundColor: AppColors.surfaceContainerHigh,
                        valueColor: AlwaysStoppedAnimation(color),
                        minHeight: 6,
                      )
                    : const SizedBox.shrink(),
                ),
              ),
              const SizedBox(width: 8),
              if (mode.risk != null)
                Text(
                  '${mode.risk!.overallScore}',
                  style: AppTypography.labelMd.copyWith(
                    color: color,
                    fontWeight: FontWeight.w700,
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildHighlightRow(String highlight) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Padding(
            padding: EdgeInsets.only(top: 6),
            child: Icon(CupertinoIcons.circle_fill, size: 6,
                color: AppColors.onSurfaceVariant),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              highlight,
              style: AppTypography.bodySm.copyWith(
                color: AppColors.onSurfaceVariant,
              ),
            ),
          ),
        ],
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
    TransportMode.bike => 'Two-wheeler',
    TransportMode.car => 'Car',
    TransportMode.metro => 'Metro',
    TransportMode.walk => 'Walk',
  };

  Color _colorForRisk(RiskLevel level) => switch (level) {
    RiskLevel.low => AppColors.riskLow,
    RiskLevel.moderate => AppColors.sunriseAmber,
    RiskLevel.high => AppColors.riskHigh,
    RiskLevel.severe => AppColors.riskSevere,
  };
}

class _StatItem extends StatelessWidget {
  final String label;
  final String value;

  const _StatItem({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: Column(
        children: [
          Text(label,
              style: AppTypography.labelCaps.copyWith(
                  color: AppColors.onSurfaceVariant)),
          const SizedBox(height: 4),
          Text(value,
              style: AppTypography.headlineMd.copyWith(
                  color: AppColors.primaryText)),
        ],
      ),
    );
  }
}
