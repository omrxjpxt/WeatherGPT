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

/// Official Alert Refined — Detailed alert view with actions and provenance
class OfficialAlertScreen extends ConsumerWidget {
  const OfficialAlertScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final alertsAsync = ref.watch(activeAlertsProvider);

    return Scaffold(
      backgroundColor: AppColors.warmIvory,
      appBar: AppBar(
        leading: IconButton(
          icon: const Icon(CupertinoIcons.back),
          onPressed: () => context.pop(),
        ),
        title: const Text('Alert Details'),
      ),
      body: alertsAsync.when(
        data: (alerts) {
          if (alerts.isEmpty) {
            return const Center(child: Text('No active alerts'));
          }
          final alert = alerts.first; // Show the primary alert
          return SingleChildScrollView(
            padding: const EdgeInsets.symmetric(horizontal: Spacing.pagePadding),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const SizedBox(height: Spacing.stackMd),

                // ── Severity Banner ──
                _buildSeverityBanner(alert),
                const SizedBox(height: Spacing.stackLg),

                // ── Alert Details ──
                WeatherCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        alert.title,
                        style: AppTypography.headlineMd.copyWith(
                          color: AppColors.primaryText,
                        ),
                      ),
                      const SizedBox(height: Spacing.stackMd),
                      Text(
                        alert.description,
                        style: AppTypography.bodyMd.copyWith(
                          color: AppColors.onSurfaceVariant,
                        ),
                      ),
                      const SizedBox(height: Spacing.stackMd),
                      const Divider(),
                      const SizedBox(height: Spacing.stackMd),

                      // ── Issued By ──
                      _InfoRow(label: 'Issued By', value: alert.issuedBy),
                      const SizedBox(height: Spacing.stackSm),
                      _InfoRow(
                        label: 'Issued At',
                        value: _formatDateTime(alert.issuedAt),
                      ),
                      if (alert.expiresAt != null) ...[
                        const SizedBox(height: Spacing.stackSm),
                        _InfoRow(
                          label: 'Expires',
                          value: _formatDateTime(alert.expiresAt!),
                        ),
                      ],
                    ],
                  ),
                ),
                const SizedBox(height: Spacing.stackLg),

                // ── Affected Areas ──
                const SectionTitle(title: 'Affected Areas'),
                const SizedBox(height: Spacing.stackMd),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: alert.affectedAreas.map((area) => Container(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                    decoration: BoxDecoration(
                      color: AppColors.surfaceContainerHigh,
                      borderRadius: BorderRadius.circular(Radii.full),
                    ),
                    child: Text(
                      area,
                      style: AppTypography.labelMd.copyWith(
                        color: AppColors.primaryText,
                      ),
                    ),
                  )).toList(),
                ),
                const SizedBox(height: Spacing.stackLg),

                // ── Action Required ──
                if (alert.actionRequired != null) ...[
                  const SectionTitle(title: 'Action Required'),
                  const SizedBox(height: Spacing.stackMd),
                  WeatherCard(
                    backgroundColor: AppColors.riskHighBg,
                    border: Border.all(
                      color: AppColors.riskHigh.withValues(alpha: 0.3),
                    ),
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Icon(CupertinoIcons.exclamationmark_shield,
                            color: AppColors.riskHigh, size: 20),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Text(
                            alert.actionRequired!,
                            style: AppTypography.bodyMd.copyWith(
                              color: AppColors.primaryText,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
                const SizedBox(height: Spacing.stackLg),

                // ── Source ──
                if (alert.source != null)
                  Row(
                    children: [
                      Icon(CupertinoIcons.doc_text, size: 14,
                          color: AppColors.onSurfaceVariant),
                      const SizedBox(width: 8),
                      Text(
                        'Source: ${alert.source}',
                        style: AppTypography.labelCaps.copyWith(
                          color: AppColors.onSurfaceVariant,
                        ),
                      ),
                    ],
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

  Widget _buildSeverityBanner(OfficialAlert alert) {
    final color = _colorForSeverity(alert.severity);
    final bgColor = _bgColorForSeverity(alert.severity);
    final label = alert.severity.name.toUpperCase();

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: BoxDecoration(
        color: bgColor,
        borderRadius: BorderRadius.circular(Radii.md),
        border: Border.all(color: color.withValues(alpha: 0.3)),
      ),
      child: Row(
        children: [
          Icon(CupertinoIcons.exclamationmark_triangle_fill,
              color: color, size: 24),
          const SizedBox(width: 12),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                label,
                style: AppTypography.labelCaps.copyWith(
                  color: color,
                  fontWeight: FontWeight.w700,
                ),
              ),
              Text(
                'Active Alert',
                style: AppTypography.bodySm.copyWith(
                  color: AppColors.onSurfaceVariant,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  String _formatDateTime(DateTime dt) {
    final hour = dt.hour > 12 ? dt.hour - 12 : (dt.hour == 0 ? 12 : dt.hour);
    final period = dt.hour >= 12 ? 'PM' : 'AM';
    return '${dt.day}/${dt.month}/${dt.year} $hour:${dt.minute.toString().padLeft(2, '0')} $period';
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

class _InfoRow extends StatelessWidget {
  final String label;
  final String value;

  const _InfoRow({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SizedBox(
          width: 80,
          child: Text(label,
              style: AppTypography.labelCaps.copyWith(
                  color: AppColors.onSurfaceVariant)),
        ),
        Expanded(
          child: Text(value,
              style: AppTypography.bodySm.copyWith(
                  color: AppColors.primaryText)),
        ),
      ],
    );
  }
}
