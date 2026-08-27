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

/// Risk & Confidence Refined — Detailed risk breakdown with confidence indicators
class RiskConfidenceScreen extends ConsumerWidget {
  const RiskConfidenceScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final tripAsync = ref.watch(tripResponseProvider);

    return Scaffold(
      backgroundColor: AppColors.warmIvory,
      appBar: AppBar(
        leading: IconButton(
          icon: const Icon(CupertinoIcons.back),
          onPressed: () => context.pop(),
        ),
        title: const Text('Risk & Confidence'),
      ),
      body: tripAsync.when(
        data: (trip) => SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: Spacing.pagePadding),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const SizedBox(height: Spacing.stackMd),

              // ── Overall Risk ──
              WeatherCard(
                child: Column(
                  children: [
                    if (trip.risk != null)
                      RiskScoreIndicator(
                        score: trip.risk!.overallScore,
                        level: trip.risk!.level,
                        size: 120,
                      ),
                    const SizedBox(height: Spacing.stackMd),
                    if (trip.risk != null)
                      RiskBadge(level: trip.risk!.level),
                    const SizedBox(height: Spacing.stackSm),
                    if (trip.risk != null)
                      Text(
                        trip.risk!.summary,
                        textAlign: TextAlign.center,
                        style: AppTypography.bodySm.copyWith(
                          color: AppColors.onSurfaceVariant,
                        ),
                      )
                    else
                      Text(
                        trip.status == TripStatus.routingUnavailable
                            ? 'Routing is currently unavailable.'
                            : 'Weather data is currently unavailable.',
                        textAlign: TextAlign.center,
                        style: AppTypography.bodySm.copyWith(
                          color: AppColors.onSurfaceVariant,
                        ),
                      ),
                  ],
                ),
              ),
              const SizedBox(height: Spacing.stackLg),

              // ── Confidence ──
              WeatherCard(
                child: Row(
                  children: [
                    Container(
                      width: 48,
                      height: 48,
                      decoration: BoxDecoration(
                        color: AppColors.softSky.withValues(alpha: 0.3),
                        borderRadius: BorderRadius.circular(Radii.md),
                      ),
                      child: Center(
                        child: Text(
                          trip.risk?.confidence.level.name.toUpperCase() ?? 'UNKNOWN',
                          style: AppTypography.labelMd.copyWith(
                            color: AppColors.tertiaryContainer,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(width: 16),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            trip.risk != null ? 'Confidence: ${trip.risk!.confidence.level.name.toUpperCase()}' : 'Confidence: UNKNOWN',
                            style: AppTypography.labelMd.copyWith(
                              color: AppColors.primaryText,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            trip.risk?.confidence.explanation ?? 'Data unavailable',
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
              const SizedBox(height: Spacing.stackLg),

              // ── Risk Factors ──
              const SectionTitle(title: 'Risk Factors'),
              const SizedBox(height: Spacing.stackMd),
              if (trip.risk != null) ...trip.risk!.factors.map((f) => _buildFactorCard(f)),
              const SizedBox(height: Spacing.stackLg),

              // ── Data Sources ──
              const SectionTitle(title: 'Data Sources'),
              const SizedBox(height: Spacing.stackMd),
              ...trip.sources.map((s) => _buildSourceRow(s)),
              const SizedBox(height: Spacing.sectionMargin),
            ],
          ),
        ),
        loading: () => const Center(
          child: CircularProgressIndicator(color: AppColors.sunriseAmber),
        ),
        error: (e, _) => Center(child: Text('Error: $e')),
      ),
    );
  }

  Widget _buildFactorCard(RiskFactor factor) {
    final color = _colorForRisk(factor.level);
    return Padding(
      padding: const EdgeInsets.only(bottom: Spacing.stackSm),
      child: WeatherCard(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Row(
                  children: [
                    Container(
                      width: 8,
                      height: 8,
                      decoration: BoxDecoration(
                        color: color,
                        shape: BoxShape.circle,
                      ),
                    ),
                    const SizedBox(width: 8),
                    Text(
                      factor.name,
                      style: AppTypography.labelMd.copyWith(
                        color: AppColors.primaryText,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ],
                ),
                Text(
                  '${factor.score}/100',
                  style: AppTypography.labelMd.copyWith(
                    color: color,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            ClipRRect(
              borderRadius: BorderRadius.circular(4),
              child: LinearProgressIndicator(
                value: factor.score / 100,
                backgroundColor: AppColors.surfaceContainerHigh,
                valueColor: AlwaysStoppedAnimation(color),
                minHeight: 6,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              factor.description,
              style: AppTypography.bodySm.copyWith(
                color: AppColors.onSurfaceVariant,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              'Weight: ${(factor.weight * 100).round()}%',
              style: AppTypography.labelCaps.copyWith(
                color: AppColors.outline,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSourceRow(DataSource source) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        children: [
          Container(
            width: 36,
            height: 36,
            decoration: BoxDecoration(
              color: AppColors.surfaceContainerHigh,
              borderRadius: BorderRadius.circular(Radii.base),
            ),
            child: Center(
              child: Text(
                source.type[0],
                style: AppTypography.labelMd.copyWith(
                  color: AppColors.primaryText,
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
                  source.name,
                  style: AppTypography.labelMd.copyWith(
                    color: AppColors.primaryText,
                  ),
                ),
                Text(
                  'Updated ${_timeAgo(source.lastUpdated)}',
                  style: AppTypography.labelCaps.copyWith(
                    color: AppColors.onSurfaceVariant,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  String _timeAgo(DateTime time) {
    final diff = DateTime.now().difference(time);
    if (diff.inMinutes < 60) return '${diff.inMinutes}m ago';
    if (diff.inHours < 24) return '${diff.inHours}h ago';
    return '${diff.inDays}d ago';
  }

  Color _colorForRisk(RiskLevel level) => switch (level) {
    RiskLevel.low => AppColors.riskLow,
    RiskLevel.moderate => AppColors.sunriseAmber,
    RiskLevel.high => AppColors.riskHigh,
    RiskLevel.severe => AppColors.riskSevere,
  };
}
