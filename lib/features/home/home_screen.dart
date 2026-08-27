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

/// WeatherGPT Home Refined — Primary dashboard screen
class HomeScreen extends ConsumerWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final weatherAsync = ref.watch(currentWeatherProvider);
    final alertsAsync = ref.watch(activeAlertsProvider);
    final tripAsync = ref.watch(tripResponseProvider);

    return Scaffold(
      backgroundColor: AppColors.warmIvory,
      body: SafeArea(
        child: Stack(
          children: [
            // ── Scrollable Content ──
            SingleChildScrollView(
              padding: const EdgeInsets.only(
                left: Spacing.pagePadding,
                right: Spacing.pagePadding,
                bottom: 120, // Sufficient padding to scroll past the floating input
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const SizedBox(height: Spacing.lg),
                  // ── Header ──
                  _buildHeader(context),
                  const SizedBox(height: Spacing.stackLg),

                  // ── Current Weather Card ──
                  weatherAsync.when(
                    data: (weather) => _buildWeatherCard(weather),
                    loading: () => const _LoadingCard(),
                    error: (_, __) => const _ErrorCard(message: 'Weather unavailable'),
                  ),
                  const SizedBox(height: Spacing.stackLg),

                  // ── Active Alerts Banner ──
                  alertsAsync.when(
                    data: (alerts) {
                      if (alerts.isEmpty) return const SizedBox.shrink();
                      return _buildAlertBanner(context, alerts.first);
                    },
                    loading: () => const SizedBox.shrink(),
                    error: (_, __) => const SizedBox.shrink(),
                  ),
                  const SizedBox(height: Spacing.stackLg),

                  // ── Quick Trip Summary ──
                  tripAsync.when(
                    data: (trip) => _buildTripSummary(context, trip),
                    loading: () => const _LoadingCard(),
                    error: (_, __) => const _ErrorCard(message: 'Trip analysis unavailable'),
                  ),
                  const SizedBox(height: Spacing.stackLg),

                  // ── AI Insight ──
                  tripAsync.when(
                    data: (trip) => _buildAIInsight(context, trip),
                    loading: () => const SizedBox.shrink(),
                    error: (_, __) => const SizedBox.shrink(),
                  ),
                  const SizedBox(height: Spacing.stackLg),

                  // ── Quick Actions ──
                  _buildQuickActions(context),
                  const SizedBox(height: Spacing.sectionMargin),
                ],
              ),
            ),

            // ── Floating Conversational Input ──
            Positioned(
              left: Spacing.pagePadding,
              right: Spacing.pagePadding,
              bottom: 16,
              child: ConversationalInputBar(
                onTap: () => context.push('/assistant'),
                onMicTap: () => context.push('/voice'),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildHeader(BuildContext context) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Good Morning',
              style: AppTypography.bodySm.copyWith(
                color: AppColors.onSurfaceVariant,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              'Noida, Sector 62',
              style: AppTypography.headlineLgMobile.copyWith(
                color: AppColors.primaryText,
              ),
            ),
          ],
        ),
        Container(
          width: 44,
          height: 44,
          decoration: BoxDecoration(
            color: AppColors.surfaceContainerHigh,
            shape: BoxShape.circle,
          ),
          child: const Icon(
            CupertinoIcons.bell,
            color: AppColors.primaryText,
            size: 20,
          ),
        ),
      ],
    );
  }

  Widget _buildWeatherCard(WeatherPoint weather) {
    return WeatherCard(
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '${weather.temperature.round()}°',
                  style: AppTypography.displayWeather.copyWith(
                    color: AppColors.primaryText,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  weather.condition,
                  style: AppTypography.bodyMd.copyWith(
                    color: AppColors.onSurfaceVariant,
                  ),
                ),
                const SizedBox(height: Spacing.stackMd),
                Row(
                  children: [
                    _WeatherDetail(label: 'Humidity', value: '${weather.humidity}%'),
                    const SizedBox(width: Spacing.md),
                    _WeatherDetail(label: 'Wind', value: '${weather.windSpeed.round()} km/h'),
                  ],
                ),
              ],
            ),
          ),
          Text(
            weather.icon,
            style: const TextStyle(fontSize: 64),
          ),
        ],
      ),
    );
  }

  Widget _buildAlertBanner(BuildContext context, OfficialAlert alert) {
    final color = switch (alert.severity) {
      AlertSeverity.emergency => AppColors.riskSevere,
      AlertSeverity.warning => AppColors.riskHigh,
      AlertSeverity.watch => AppColors.sunriseAmber,
      AlertSeverity.advisory => AppColors.riskModerate,
    };
    final bgColor = switch (alert.severity) {
      AlertSeverity.emergency => AppColors.riskSevereBg,
      AlertSeverity.warning => AppColors.riskHighBg,
      AlertSeverity.watch => AppColors.riskModerateBg,
      AlertSeverity.advisory => AppColors.riskModerateBg,
    };

    return GestureDetector(
      onTap: () => context.push('/alert-detail'),
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: bgColor,
          borderRadius: BorderRadius.circular(Radii.md),
          border: Border.all(color: color.withValues(alpha: 0.3)),
        ),
        child: Row(
          children: [
            Icon(CupertinoIcons.exclamationmark_triangle_fill,
                color: color, size: 20),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    alert.title,
                    style: AppTypography.labelMd.copyWith(
                      color: color,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    alert.issuedBy,
                    style: AppTypography.labelCaps.copyWith(
                      color: AppColors.onSurfaceVariant,
                    ),
                  ),
                ],
              ),
            ),
            Icon(CupertinoIcons.chevron_right, color: color, size: 16),
          ],
        ),
      ),
    );
  }

  Widget _buildTripSummary(BuildContext context, TripResponse trip) {
    return WeatherCard(
      onTap: () => context.push('/trips'),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const SectionTitle(title: 'Your Commute'),
              RiskBadge(level: trip.risk.level),
            ],
          ),
          const SizedBox(height: Spacing.stackMd),
          // Route summary
          Row(
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    trip.request.origin,
                    style: AppTypography.labelMd.copyWith(
                      color: AppColors.primaryText,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Row(
                    children: [
                      Icon(Icons.arrow_downward, size: 14,
                          color: AppColors.onSurfaceVariant),
                      const SizedBox(width: 4),
                      Text(
                        '${trip.distanceKm} km • ${trip.estimatedDuration.inMinutes} min',
                        style: AppTypography.bodySm.copyWith(
                          color: AppColors.onSurfaceVariant,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 4),
                  Text(
                    trip.request.destination,
                    style: AppTypography.labelMd.copyWith(
                      color: AppColors.primaryText,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ],
              ),
              const Spacer(),
              RiskScoreIndicator(
                score: trip.risk.overallScore,
                level: trip.risk.level,
                size: 72,
              ),
            ],
          ),
          const SizedBox(height: Spacing.stackMd),
          // Recommendation snippet
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: AppColors.surfaceContainerLow,
              borderRadius: BorderRadius.circular(Radii.md),
            ),
            child: Row(
              children: [
                const Icon(CupertinoIcons.lightbulb, size: 16,
                    color: AppColors.sunriseAmber),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    trip.recommendation.headline,
                    style: AppTypography.bodySm.copyWith(
                      color: AppColors.primaryText,
                    ),
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildAIInsight(BuildContext context, TripResponse trip) {
    return WeatherCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: AppColors.sunriseAmber.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(Radii.base),
                ),
                child: const Icon(CupertinoIcons.sparkles,
                    color: AppColors.sunriseAmber, size: 18),
              ),
              const SizedBox(width: 12),
              Text(
                'AI Insight',
                style: AppTypography.headlineMd.copyWith(
                  color: AppColors.primaryText,
                ),
              ),
            ],
          ),
          const SizedBox(height: Spacing.stackMd),
          Text(
            trip.risk.summary,
            style: AppTypography.bodyMd.copyWith(
              color: AppColors.onSurfaceVariant,
            ),
          ),
          const SizedBox(height: Spacing.stackMd),
          // Data sources
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: trip.sources
                .map((s) => _SourceChip(source: s))
                .toList(),
          ),
        ],
      ),
    );
  }

  Widget _buildQuickActions(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const SectionTitle(title: 'Explore'),
        const SizedBox(height: Spacing.stackMd),
        Row(
          children: [
            Expanded(
              child: _QuickActionCard(
                icon: CupertinoIcons.slider_horizontal_3,
                label: 'What-If',
                onTap: () => context.push('/what-if'),
              ),
            ),
            const SizedBox(width: Spacing.gutter),
            Expanded(
              child: _QuickActionCard(
                icon: CupertinoIcons.arrow_right_arrow_left,
                label: 'Compare Modes',
                onTap: () => context.push('/mode-comparison'),
              ),
            ),
          ],
        ),
        const SizedBox(height: Spacing.gutter),
        Row(
          children: [
            Expanded(
              child: _QuickActionCard(
                icon: CupertinoIcons.clock,
                label: 'History',
                onTap: () => context.push('/history'),
              ),
            ),
            const SizedBox(width: Spacing.gutter),
            Expanded(
              child: _QuickActionCard(
                icon: CupertinoIcons.map_pin_ellipse,
                label: 'Hazards',
                onTap: () => context.push('/hazard'),
              ),
            ),
          ],
        ),
      ],
    );
  }
}

// ── Private Helper Widgets ──

class _WeatherDetail extends StatelessWidget {
  final String label;
  final String value;

  const _WeatherDetail({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label,
            style: AppTypography.labelCaps.copyWith(
                color: AppColors.onSurfaceVariant)),
        const SizedBox(height: 2),
        Text(value,
            style: AppTypography.labelMd.copyWith(
                color: AppColors.primaryText, fontWeight: FontWeight.w600)),
      ],
    );
  }
}

class _SourceChip extends StatelessWidget {
  final DataSource source;

  const _SourceChip({required this.source});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: AppColors.surfaceContainerHigh,
        borderRadius: BorderRadius.circular(Radii.full),
      ),
      child: Text(
        source.type,
        style: AppTypography.labelCaps.copyWith(
          color: AppColors.onSurfaceVariant,
        ),
      ),
    );
  }
}

class _QuickActionCard extends StatelessWidget {
  final IconData icon;
  final String label;
  final VoidCallback onTap;

  const _QuickActionCard({
    required this.icon,
    required this.label,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return WeatherCard(
      onTap: onTap,
      padding: const EdgeInsets.all(Spacing.md),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: AppColors.sunriseAmber, size: 24),
          const SizedBox(height: Spacing.stackSm),
          Text(
            label,
            style: AppTypography.labelMd.copyWith(
              color: AppColors.primaryText,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }
}

class _LoadingCard extends StatelessWidget {
  const _LoadingCard();

  @override
  Widget build(BuildContext context) {
    return WeatherCard(
      child: SizedBox(
        height: 120,
        child: Center(
          child: CircularProgressIndicator(
            color: AppColors.sunriseAmber,
            strokeWidth: 2,
          ),
        ),
      ),
    );
  }
}

class _ErrorCard extends StatelessWidget {
  final String message;

  const _ErrorCard({required this.message});

  @override
  Widget build(BuildContext context) {
    return WeatherCard(
      child: Padding(
        padding: const EdgeInsets.all(Spacing.md),
        child: Text(
          message,
          style: AppTypography.bodySm.copyWith(
            color: AppColors.onSurfaceVariant,
          ),
        ),
      ),
    );
  }
}
