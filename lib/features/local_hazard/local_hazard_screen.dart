import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:go_router/go_router.dart';
import 'package:latlong2/latlong.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_typography.dart';
import '../../core/theme/tokens.dart';
import '../../core/widgets/widgets.dart';
import '../../core/providers.dart';
import '../../models/models.dart';

/// Local Hazard Refined — Map-centric hazard detail view
class LocalHazardScreen extends ConsumerWidget {
  const LocalHazardScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final tripAsync = ref.watch(tripResponseProvider);

    return Scaffold(
      backgroundColor: AppColors.warmIvory,
      body: tripAsync.when(
        data: (trip) => _LocalHazardBody(hazards: trip.hazards),
        loading: () => const Center(
          child: CircularProgressIndicator(color: AppColors.sunriseAmber),
        ),
        error: (e, _) => Center(child: Text('Error: $e')),
      ),
    );
  }
}

class _LocalHazardBody extends StatelessWidget {
  final List<Hazard> hazards;

  const _LocalHazardBody({required this.hazards});

  @override
  Widget build(BuildContext context) {
    final primary = hazards.isNotEmpty ? hazards.first : null;

    return CustomScrollView(
      slivers: [
        // ── Map ──
        SliverToBoxAdapter(
          child: SizedBox(
            height: 280,
            child: Stack(
              children: [
                _HazardMap(hazards: hazards),
                Positioned(
                  top: MediaQuery.of(context).padding.top + 8,
                  left: Spacing.pagePadding,
                  child: GestureDetector(
                    onTap: () => context.pop(),
                    child: Container(
                      width: 40,
                      height: 40,
                      decoration: BoxDecoration(
                        color: AppColors.cardBackground.withValues(alpha: 0.9),
                        shape: BoxShape.circle,
                      ),
                      child: const Icon(CupertinoIcons.back,
                          size: 20, color: AppColors.primaryText),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),

        // ── Hazard Details ──
        SliverPadding(
          padding: const EdgeInsets.all(Spacing.pagePadding),
          sliver: SliverList(
            delegate: SliverChildListDelegate([
              if (primary != null) ...[
                // Primary hazard card
                WeatherCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Container(
                            width: 44,
                            height: 44,
                            decoration: BoxDecoration(
                              color: _colorForRisk(primary.severity)
                                  .withValues(alpha: 0.15),
                              borderRadius: BorderRadius.circular(Radii.md),
                            ),
                            child: Icon(
                              _iconForHazard(primary.type),
                              color: _colorForRisk(primary.severity),
                              size: 24,
                            ),
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  primary.title,
                                  style: AppTypography.headlineMd.copyWith(
                                    color: AppColors.primaryText,
                                  ),
                                ),
                                const SizedBox(height: 4),
                                RiskBadge(level: primary.severity),
                              ],
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: Spacing.stackMd),
                      Text(
                        primary.description,
                        style: AppTypography.bodyMd.copyWith(
                          color: AppColors.onSurfaceVariant,
                        ),
                      ),
                      const SizedBox(height: Spacing.stackMd),
                      const Divider(),
                      const SizedBox(height: Spacing.stackSm),
                      if (primary.reportedAt != null)
                        _InfoRow(label: 'Reported', value: _timeAgo(primary.reportedAt!)),
                      if (primary.source != null) ...[
                        const SizedBox(height: 4),
                        _InfoRow(label: 'Source', value: primary.source!),
                      ],
                    ],
                  ),
                ),
                const SizedBox(height: Spacing.stackLg),
              ],

              // All hazards
              if (hazards.length > 1) ...[
                const SectionTitle(title: 'Other Hazards'),
                const SizedBox(height: Spacing.stackMd),
                ...hazards.skip(1).map((h) => _buildHazardListItem(h)),
              ],
              const SizedBox(height: Spacing.sectionMargin),
            ]),
          ),
        ),
      ],
    );
  }

  Widget _buildHazardListItem(Hazard hazard) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: WeatherCard(
        padding: const EdgeInsets.all(16),
        child: Row(
          children: [
            Icon(
              _iconForHazard(hazard.type),
              color: _colorForRisk(hazard.severity),
              size: 24,
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(hazard.title,
                      style: AppTypography.labelMd.copyWith(
                          color: AppColors.primaryText,
                          fontWeight: FontWeight.w600)),
                  Text(hazard.source ?? '',
                      style: AppTypography.labelCaps.copyWith(
                          color: AppColors.onSurfaceVariant)),
                ],
              ),
            ),
            RiskBadge(level: hazard.severity, showDot: false),
          ],
        ),
      ),
    );
  }

  IconData _iconForHazard(HazardType type) => switch (type) {
    HazardType.waterlogging => CupertinoIcons.drop_fill,
    HazardType.fog => CupertinoIcons.cloud_fog,
    HazardType.heavyRain => CupertinoIcons.cloud_heavyrain,
    HazardType.storm => CupertinoIcons.bolt_fill,
    HazardType.heatwave => CupertinoIcons.sun_max_fill,
    HazardType.construction => CupertinoIcons.hammer,
  };

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

class _HazardMap extends StatelessWidget {
  final List<Hazard> hazards;

  const _HazardMap({required this.hazards});

  @override
  Widget build(BuildContext context) {
    final markers = hazards.map((h) => Marker(
      point: LatLng(h.lat, h.lng),
      width: 36,
      height: 36,
      child: Container(
        decoration: BoxDecoration(
          color: AppColors.riskSevere,
          shape: BoxShape.circle,
          border: Border.all(color: Colors.white, width: 2),
          boxShadow: const [
            BoxShadow(offset: Offset(0, 2), blurRadius: 8, color: AppColors.softShadow),
          ],
        ),
        child: const Icon(CupertinoIcons.exclamationmark_triangle_fill,
            color: Colors.white, size: 18),
      ),
    )).toList();

    final center = hazards.isNotEmpty
        ? LatLng(hazards.first.lat, hazards.first.lng)
        : const LatLng(28.55, 77.15);

    return FlutterMap(
      options: MapOptions(
        initialCenter: center,
        initialZoom: 13,
      ),
      children: [
        TileLayer(
          urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
          userAgentPackageName: 'com.weathergpt.weather_gpt',
          tileBuilder: (context, tileWidget, tile) {
            return ColorFiltered(
              colorFilter: const ColorFilter.matrix(<double>[
                0.95, 0.05, 0.00, 0, 10,
                0.02, 0.90, 0.05, 0, 10,
                0.02, 0.05, 0.85, 0, 10,
                0.00, 0.00, 0.00, 1, 0,
              ]),
              child: tileWidget,
            );
          },
        ),
        MarkerLayer(markers: markers),
      ],
    );
  }
}

class _InfoRow extends StatelessWidget {
  final String label;
  final String value;

  const _InfoRow({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        SizedBox(
          width: 70,
          child: Text(label,
              style: AppTypography.labelCaps.copyWith(
                  color: AppColors.onSurfaceVariant)),
        ),
        Text(value,
            style: AppTypography.bodySm.copyWith(
                color: AppColors.primaryText)),
      ],
    );
  }
}
