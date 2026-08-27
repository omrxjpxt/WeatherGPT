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

/// Historical Replay Refined — Past weather events with timeline
class HistoricalReplayScreen extends ConsumerWidget {
  const HistoricalReplayScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final historyAsync = ref.watch(historicalEventsProvider);

    return Scaffold(
      backgroundColor: AppColors.warmIvory,
      appBar: AppBar(
        leading: IconButton(
          icon: const Icon(CupertinoIcons.back),
          onPressed: () => context.pop(),
        ),
        title: const Text('Historical Replay'),
      ),
      body: historyAsync.when(
        data: (events) => ListView.builder(
          padding: const EdgeInsets.all(Spacing.pagePadding),
          itemCount: events.length,
          itemBuilder: (context, index) {
            return _EventCard(event: events[index]);
          },
        ),
        loading: () => const Center(
          child: CircularProgressIndicator(color: AppColors.sunriseAmber),
        ),
        error: (e, _) => Center(child: Text('Error: $e')),
      ),
    );
  }
}

class _EventCard extends StatefulWidget {
  final HistoricalEvent event;

  const _EventCard({required this.event});

  @override
  State<_EventCard> createState() => _EventCardState();
}

class _EventCardState extends State<_EventCard> {
  bool _expanded = false;

  @override
  Widget build(BuildContext context) {
    final color = _colorForRisk(widget.event.severity);

    return Padding(
      padding: const EdgeInsets.only(bottom: Spacing.stackMd),
      child: WeatherCard(
        onTap: () => setState(() => _expanded = !_expanded),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  width: 44,
                  height: 44,
                  decoration: BoxDecoration(
                    color: color.withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(Radii.md),
                  ),
                  child: Icon(
                    CupertinoIcons.clock_fill,
                    color: color,
                    size: 22,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        widget.event.title,
                        style: AppTypography.headlineMd.copyWith(
                          color: AppColors.primaryText,
                          fontSize: 16,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        _formatDate(widget.event.date),
                        style: AppTypography.labelCaps.copyWith(
                          color: AppColors.onSurfaceVariant,
                        ),
                      ),
                    ],
                  ),
                ),
                RiskBadge(level: widget.event.severity, showDot: false),
              ],
            ),
            const SizedBox(height: Spacing.stackMd),
            Text(
              widget.event.description,
              style: AppTypography.bodySm.copyWith(
                color: AppColors.onSurfaceVariant,
              ),
            ),

            // Expanded content
            AnimatedCrossFade(
              firstChild: const SizedBox.shrink(),
              secondChild: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const SizedBox(height: Spacing.stackMd),
                  const Divider(),
                  const SizedBox(height: Spacing.stackMd),

                  // Impacts
                  const SectionTitle(title: 'Impacts'),
                  const SizedBox(height: Spacing.stackSm),
                  ...widget.event.impacts.map((impact) => Padding(
                    padding: const EdgeInsets.only(bottom: 6),
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Padding(
                          padding: const EdgeInsets.only(top: 6),
                          child: Container(
                            width: 6,
                            height: 6,
                            decoration: BoxDecoration(
                              color: color,
                              shape: BoxShape.circle,
                            ),
                          ),
                        ),
                        const SizedBox(width: 10),
                        Expanded(
                          child: Text(
                            impact,
                            style: AppTypography.bodySm.copyWith(
                              color: AppColors.onSurfaceVariant,
                            ),
                          ),
                        ),
                      ],
                    ),
                  )),

                  // Weather timeline
                  const SizedBox(height: Spacing.stackMd),
                  const SectionTitle(title: 'Weather Timeline'),
                  const SizedBox(height: Spacing.stackMd),
                  SizedBox(
                    height: 120,
                    child: _WeatherTimeline(
                      points: widget.event.weatherTimeline,
                    ),
                  ),
                ],
              ),
              crossFadeState: _expanded
                  ? CrossFadeState.showSecond
                  : CrossFadeState.showFirst,
              duration: const Duration(milliseconds: 300),
            ),
            const SizedBox(height: Spacing.stackSm),
            Center(
              child: Icon(
                _expanded
                    ? CupertinoIcons.chevron_up
                    : CupertinoIcons.chevron_down,
                size: 16,
                color: AppColors.onSurfaceVariant,
              ),
            ),
          ],
        ),
      ),
    );
  }

  String _formatDate(DateTime dt) {
    const months = [
      'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
      'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'
    ];
    return '${months[dt.month - 1]} ${dt.day}, ${dt.year}';
  }

  Color _colorForRisk(RiskLevel level) => switch (level) {
    RiskLevel.low => AppColors.riskLow,
    RiskLevel.moderate => AppColors.sunriseAmber,
    RiskLevel.high => AppColors.riskHigh,
    RiskLevel.severe => AppColors.riskSevere,
  };
}

/// Simple precipitation bar chart for weather timeline
class _WeatherTimeline extends StatelessWidget {
  final List<WeatherPoint> points;

  const _WeatherTimeline({required this.points});

  @override
  Widget build(BuildContext context) {
    final maxPrecip = points
        .map((p) => p.precipitation)
        .reduce((a, b) => a > b ? a : b)
        .clamp(1.0, double.infinity);

    return Row(
      crossAxisAlignment: CrossAxisAlignment.end,
      children: points.asMap().entries.map((entry) {
        final idx = entry.key;
        final point = entry.value;
        final height = (point.precipitation / maxPrecip) * 80 + 8;
        final isHeavy = point.precipitation > 20;

        return Expanded(
          child: Padding(
            padding: EdgeInsets.only(right: idx < points.length - 1 ? 3 : 0),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                Text(
                  point.icon,
                  style: const TextStyle(fontSize: 12),
                ),
                const SizedBox(height: 4),
                Container(
                  height: height,
                  decoration: BoxDecoration(
                    color: isHeavy ? AppColors.riskHigh : AppColors.softSky,
                    borderRadius: BorderRadius.circular(3),
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  '${point.time.hour}',
                  style: AppTypography.labelCaps.copyWith(
                    color: AppColors.onSurfaceVariant,
                    fontSize: 9,
                  ),
                ),
              ],
            ),
          ),
        );
      }).toList(),
    );
  }
}
