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

/// Alerts Feed Refined — List of active alerts with severity indicators
class AlertsFeedScreen extends ConsumerWidget {
  const AlertsFeedScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final alertsAsync = ref.watch(activeAlertsProvider);

    return Scaffold(
      backgroundColor: AppColors.warmIvory,
      body: SafeArea(
        child: CustomScrollView(
          slivers: [
            SliverPadding(
              padding: const EdgeInsets.all(Spacing.pagePadding),
              sliver: SliverList(
                delegate: SliverChildListDelegate([
                  Text(
                    'Alerts',
                    style: AppTypography.headlineLgMobile.copyWith(
                      color: AppColors.primaryText,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    'Active weather & traffic alerts for Delhi-NCR',
                    style: AppTypography.bodySm.copyWith(
                      color: AppColors.onSurfaceVariant,
                    ),
                  ),
                  const SizedBox(height: Spacing.stackLg),
                ]),
              ),
            ),
            alertsAsync.when(
              data: (alerts) => SliverPadding(
                padding: const EdgeInsets.symmetric(horizontal: Spacing.pagePadding),
                sliver: SliverList(
                  delegate: SliverChildBuilderDelegate(
                    (context, index) {
                      final alert = alerts[index];
                      return Padding(
                        padding: const EdgeInsets.only(bottom: Spacing.stackMd),
                        child: _AlertCard(alert: alert),
                      );
                    },
                    childCount: alerts.length,
                  ),
                ),
              ),
              loading: () => const SliverFillRemaining(
                child: Center(
                  child: CircularProgressIndicator(color: AppColors.sunriseAmber),
                ),
              ),
              error: (e, _) => SliverFillRemaining(
                child: Center(child: Text('Error: $e')),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _AlertCard extends StatelessWidget {
  final OfficialAlert alert;

  const _AlertCard({required this.alert});

  @override
  Widget build(BuildContext context) {
    final color = _colorForSeverity(alert.severity);
    final bgColor = _bgColorForSeverity(alert.severity);

    return GestureDetector(
      onTap: () => context.push('/alert-detail'),
      child: WeatherCard(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                // Severity indicator
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(
                    color: bgColor,
                    borderRadius: BorderRadius.circular(Radii.badge),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Container(
                        width: 6,
                        height: 6,
                        decoration: BoxDecoration(
                          color: color,
                          shape: BoxShape.circle,
                        ),
                      ),
                      const SizedBox(width: 6),
                      Text(
                        alert.severity.name.toUpperCase(),
                        style: AppTypography.labelCaps.copyWith(
                          color: color,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ],
                  ),
                ),
                const Spacer(),
                Text(
                  _timeAgo(alert.issuedAt),
                  style: AppTypography.labelCaps.copyWith(
                    color: AppColors.onSurfaceVariant,
                  ),
                ),
              ],
            ),
            const SizedBox(height: Spacing.stackMd),
            Text(
              alert.title,
              style: AppTypography.headlineMd.copyWith(
                color: AppColors.primaryText,
                fontSize: 18,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              alert.description,
              style: AppTypography.bodySm.copyWith(
                color: AppColors.onSurfaceVariant,
              ),
              maxLines: 3,
              overflow: TextOverflow.ellipsis,
            ),
            const SizedBox(height: Spacing.stackMd),
            // Affected areas chips
            Wrap(
              spacing: 6,
              runSpacing: 6,
              children: alert.affectedAreas.take(4).map((area) => Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: AppColors.surfaceContainerHigh,
                  borderRadius: BorderRadius.circular(Radii.full),
                ),
                child: Text(
                  area,
                  style: AppTypography.labelCaps.copyWith(
                    color: AppColors.onSurfaceVariant,
                    fontSize: 10,
                  ),
                ),
              )).toList(),
            ),
            const SizedBox(height: Spacing.stackMd),
            Row(
              children: [
                Text(
                  alert.issuedBy,
                  style: AppTypography.labelCaps.copyWith(
                    color: AppColors.outline,
                  ),
                ),
                const Spacer(),
                Icon(CupertinoIcons.chevron_right,
                    size: 14, color: AppColors.onSurfaceVariant),
              ],
            ),
          ],
        ),
      ),
    );
  }

  String _timeAgo(DateTime time) {
    final diff = DateTime.now().difference(time);
    if (diff.inMinutes < 60) return '${diff.inMinutes}m ago';
    if (diff.inHours < 24) return '${diff.inHours}h ago';
    return '${diff.inDays}d ago';
  }

  Color _colorForSeverity(AlertSeverity s) => switch (s) {
    AlertSeverity.emergency => AppColors.riskSevere,
    AlertSeverity.warning => AppColors.riskHigh,
    AlertSeverity.watch => AppColors.sunriseAmber,
    AlertSeverity.advisory => AppColors.riskModerate,
  };

  Color _bgColorForSeverity(AlertSeverity s) => switch (s) {
    AlertSeverity.emergency => AppColors.riskSevereBg,
    AlertSeverity.warning => AppColors.riskHighBg,
    AlertSeverity.watch => AppColors.riskModerateBg,
    AlertSeverity.advisory => AppColors.riskModerateBg,
  };
}
