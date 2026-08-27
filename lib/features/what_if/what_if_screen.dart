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

/// What-If Simulator Refined — Interactive departure time slider
class WhatIfScreen extends ConsumerStatefulWidget {
  const WhatIfScreen({super.key});

  @override
  ConsumerState<WhatIfScreen> createState() => _WhatIfScreenState();
}

class _WhatIfScreenState extends ConsumerState<WhatIfScreen> {
  double _sliderValue = 4; // index 4 = 8:00 AM (base: 6:00 AM + 4*30 min)
  late List<ScenarioResult> _scenarios;
  bool _loaded = false;

  @override
  Widget build(BuildContext context) {
    final scenariosAsync = ref.watch(scenarioResultsProvider);

    return Scaffold(
      backgroundColor: AppColors.warmIvory,
      appBar: AppBar(
        backgroundColor: AppColors.warmIvory,
        leading: IconButton(
          icon: const Icon(CupertinoIcons.back),
          onPressed: () => context.pop(),
        ),
        title: const Text('What-If Simulator'),
      ),
      body: scenariosAsync.when(
        data: (scenarios) {
          _scenarios = scenarios;
          _loaded = true;
          final idx = _sliderValue.round().clamp(0, scenarios.length - 1);
          final current = scenarios[idx];

          return SingleChildScrollView(
            padding: const EdgeInsets.symmetric(horizontal: Spacing.pagePadding),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const SizedBox(height: Spacing.stackMd),

                // ── Departure Time Header ──
                WeatherCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const SectionTitle(title: 'Departure Time'),
                      const SizedBox(height: Spacing.stackMd),
                      Center(
                        child: Text(
                          _formatTime(current.departureTime),
                          style: AppTypography.headlineLg.copyWith(
                            color: AppColors.primaryText,
                          ),
                        ),
                      ),
                      const SizedBox(height: Spacing.stackMd),

                      // ── Slider ──
                      SliderTheme(
                        data: SliderThemeData(
                          activeTrackColor: AppColors.sunriseAmber,
                          inactiveTrackColor: AppColors.sliderTrack,
                          thumbColor: AppColors.sliderThumb,
                          thumbShape: const RoundSliderThumbShape(
                            enabledThumbRadius: 14,
                            elevation: 4,
                          ),
                          overlayColor: AppColors.sunriseAmber.withValues(alpha: 0.15),
                          trackHeight: 6,
                        ),
                        child: Slider(
                          value: _sliderValue,
                          min: 0,
                          max: (scenarios.length - 1).toDouble(),
                          divisions: scenarios.length - 1,
                          onChanged: (v) => setState(() => _sliderValue = v),
                        ),
                      ),
                      // Time range labels
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Text(
                            _formatTime(scenarios.first.departureTime),
                            style: AppTypography.labelCaps.copyWith(
                              color: AppColors.onSurfaceVariant,
                            ),
                          ),
                          Text(
                            _formatTime(scenarios.last.departureTime),
                            style: AppTypography.labelCaps.copyWith(
                              color: AppColors.onSurfaceVariant,
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: Spacing.stackLg),

                // ── Risk Score ──
                AnimatedSwitcher(
                  duration: const Duration(milliseconds: 300),
                  child: WeatherCard(
                    key: ValueKey(idx),
                    child: Row(
                      children: [
                        if (current.risk != null) ...[
                          RiskScoreIndicator(
                            score: current.risk!.overallScore,
                            level: current.risk!.level,
                            size: 64,
                          ),
                        ],
                        const SizedBox(width: Spacing.md),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              if (current.risk != null)
                                RiskBadge(level: current.risk!.level),
                              const SizedBox(height: 4),
                              Text(
                                current.recommendation ?? '',
                                style: AppTypography.bodySm.copyWith(
                                  color: AppColors.onSurfaceVariant,
                                ),
                                maxLines: 3,
                                overflow: TextOverflow.ellipsis,
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: Spacing.stackLg),

                // ── Timeline ──
                const SectionTitle(title: 'Risk Timeline'),
                const SizedBox(height: Spacing.stackMd),
                SizedBox(
                  height: 160,
                  child: _RiskTimeline(
                    scenarios: scenarios,
                    selectedIndex: idx,
                  ),
                ),
                const SizedBox(height: Spacing.stackLg),

                // ── Changed Factors ──
                const SectionTitle(title: 'Key Factors'),
                const SizedBox(height: Spacing.stackSm),
                ...current.changedFactors.map((f) => _buildFactorRow(f)),
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

  Widget _buildFactorRow(RiskFactor factor) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: WeatherCard(
        padding: const EdgeInsets.all(16),
        child: Row(
          children: [
            Container(
              width: 40,
              height: 40,
              decoration: BoxDecoration(
                color: _colorForRisk(factor.level).withValues(alpha: 0.15),
                borderRadius: BorderRadius.circular(Radii.base),
              ),
              child: Center(
                child: Text(
                  '${factor.score}',
                  style: AppTypography.labelMd.copyWith(
                    color: _colorForRisk(factor.level),
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    factor.name,
                    style: AppTypography.labelMd.copyWith(
                      color: AppColors.primaryText,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  Text(
                    factor.description,
                    style: AppTypography.bodySm.copyWith(
                      color: AppColors.onSurfaceVariant,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  String _formatTime(DateTime time) {
    final hour = time.hour;
    final minute = time.minute.toString().padLeft(2, '0');
    final period = hour >= 12 ? 'PM' : 'AM';
    final displayHour = hour > 12 ? hour - 12 : (hour == 0 ? 12 : hour);
    return '$displayHour:$minute $period';
  }

  Color _colorForRisk(RiskLevel level) => switch (level) {
    RiskLevel.low => AppColors.riskLow,
    RiskLevel.moderate => AppColors.riskModerate,
    RiskLevel.high => AppColors.riskHigh,
    RiskLevel.severe => AppColors.riskSevere,
  };
}

/// Visual timeline chart showing risk scores across departure times
class _RiskTimeline extends StatelessWidget {
  final List<ScenarioResult> scenarios;
  final int selectedIndex;

  const _RiskTimeline({required this.scenarios, required this.selectedIndex});

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final barWidth = (constraints.maxWidth - (scenarios.length - 1) * 4) /
            scenarios.length;

        return Row(
          crossAxisAlignment: CrossAxisAlignment.end,
          children: scenarios.asMap().entries.map((entry) {
            final idx = entry.key;
            final scenario = entry.value;
            final isSelected = idx == selectedIndex;
            final height = scenario.risk != null ? (scenario.risk!.overallScore / 100) * 120 + 20 : 20.0;
            final color = scenario.risk != null ? _colorForRisk(scenario.risk!.level) : AppColors.outline;

            return Padding(
              padding: EdgeInsets.only(right: idx < scenarios.length - 1 ? 4 : 0),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  if (isSelected)
                    if (scenario.risk != null)
                      Text(
                        '${scenario.risk!.overallScore}',
                        style: AppTypography.labelMd.copyWith(
                          color: isSelected ? AppColors.surface : color,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                  const SizedBox(height: 4),
                  AnimatedContainer(
                    duration: const Duration(milliseconds: 300),
                    curve: Curves.easeInOut,
                    width: barWidth,
                    height: height,
                    decoration: BoxDecoration(
                      color: isSelected ? color : color.withValues(alpha: 0.4),
                      borderRadius: BorderRadius.circular(4),
                    ),
                  ),
                  const SizedBox(height: 4),
                  if (idx % 2 == 0)
                    Text(
                      _shortTime(scenario.departureTime),
                      style: AppTypography.labelCaps.copyWith(
                        color: AppColors.onSurfaceVariant,
                        fontSize: 9,
                      ),
                    ),
                ],
              ),
            );
          }).toList(),
        );
      },
    );
  }

  String _shortTime(DateTime time) {
    final hour = time.hour;
    final period = hour >= 12 ? 'P' : 'A';
    final displayHour = hour > 12 ? hour - 12 : (hour == 0 ? 12 : hour);
    return '$displayHour$period';
  }

  Color _colorForRisk(RiskLevel level) => switch (level) {
    RiskLevel.low => AppColors.riskLow,
    RiskLevel.moderate => AppColors.sunriseAmber,
    RiskLevel.high => AppColors.riskHigh,
    RiskLevel.severe => AppColors.riskSevere,
  };
}
