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

/// Trip Analysis Refined — Route map with risk segments and trip details
class TripAnalysisScreen extends ConsumerWidget {
  const TripAnalysisScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final tripAsync = ref.watch(tripResponseProvider);

    return Scaffold(
      backgroundColor: AppColors.warmIvory,
      body: tripAsync.when(
        data: (trip) => _TripAnalysisBody(trip: trip),
        loading: () => const Center(
          child: CircularProgressIndicator(color: AppColors.sunriseAmber),
        ),
        error: (e, _) => Center(child: Text('Error: $e')),
      ),
    );
  }
}

class _TripAnalysisBody extends StatelessWidget {
  final TripResponse trip;

  const _TripAnalysisBody({required this.trip});

  @override
  Widget build(BuildContext context) {
    return CustomScrollView(
      slivers: [
        // ── Map Section ──
        SliverToBoxAdapter(
          child: SizedBox(
            height: 320,
            child: Stack(
              children: [
                _RouteMap(segments: trip.route, hazards: trip.hazards),
                // Back button & header overlay
                Positioned(
                  top: MediaQuery.of(context).padding.top + 8,
                  left: Spacing.pagePadding,
                  child: _CircleButton(
                    icon: CupertinoIcons.back,
                    onTap: () {
                      if (context.canPop()) context.pop();
                    },
                  ),
                ),
                // Map overlay card
                Positioned(
                  bottom: 16,
                  left: Spacing.pagePadding,
                  right: Spacing.pagePadding,
                  child: Container(
                    padding: const EdgeInsets.symmetric(
                        horizontal: 16, vertical: 12),
                    decoration: BoxDecoration(
                      color: AppColors.cardBackground.withValues(alpha: 0.95),
                      borderRadius: BorderRadius.circular(Radii.card),
                      boxShadow: const [
                        BoxShadow(
                          offset: Offset(0, 4),
                          blurRadius: 16,
                          color: AppColors.softShadow,
                        ),
                      ],
                    ),
                    child: Row(
                      children: [
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Text(
                                '${trip.request.origin} → ${trip.request.destination}',
                                style: AppTypography.labelMd.copyWith(
                                  color: AppColors.primaryText,
                                  fontWeight: FontWeight.w600,
                                ),
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                              ),
                              const SizedBox(height: 4),
                              Text(
                                '${trip.distanceKm} km • ${trip.estimatedDuration.inMinutes} min • ${_modeLabel(trip.request.mode)}',
                                style: AppTypography.bodySm.copyWith(
                                  color: AppColors.onSurfaceVariant,
                                ),
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(width: 12),
                        if (trip.risk != null)
                          RiskBadge(level: trip.risk!.level),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),

        // ── Trip Details ──
        SliverPadding(
          padding: const EdgeInsets.all(Spacing.pagePadding),
          sliver: SliverList(
            delegate: SliverChildListDelegate([
              // Risk summary card
              _buildRiskCard(context, trip),
              const SizedBox(height: Spacing.stackMd),

              // Route segments
              const SectionTitle(title: 'Route Segments'),
              const SizedBox(height: Spacing.stackSm),
              ...trip.route.map((seg) => _buildSegmentRow(seg)),
              const SizedBox(height: Spacing.stackLg),

              // Hazards
              if (trip.hazards.isNotEmpty) ...[
                const SectionTitle(title: 'Hazards'),
                const SizedBox(height: Spacing.stackSm),
                ...trip.hazards.map((h) => _buildHazardCard(context, h)),
                const SizedBox(height: Spacing.stackLg),
              ],

              // Recommendation
              _buildRecommendationCard(context, trip),
              const SizedBox(height: Spacing.stackLg),

              // Action buttons
              _buildActionButtons(context),
              const SizedBox(height: Spacing.sectionMargin),
            ]),
          ),
        ),
      ],
    );
  }

  Widget _buildRiskCard(BuildContext context, TripResponse trip) {
    return WeatherCard(
      child: Row(
        children: [
          if (trip.risk != null)
            RiskScoreIndicator(
              score: trip.risk!.overallScore,
              level: trip.risk!.level,
            ),
          const SizedBox(width: Spacing.md),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                if (trip.risk != null) RiskBadge(level: trip.risk!.level),
                const SizedBox(height: 8),
                if (trip.risk != null)
                  Text(
                    trip.risk!.summary,
                    style: AppTypography.bodySm.copyWith(
                      color: AppColors.onSurfaceVariant,
                    ),
                    maxLines: 3,
                    overflow: TextOverflow.ellipsis,
                  )
                else
                  Text(
                    trip.status == TripStatus.routingUnavailable
                        ? 'Routing is currently unavailable.'
                        : 'Weather data is currently unavailable.',
                    style: AppTypography.bodySm.copyWith(
                      color: AppColors.onSurfaceVariant,
                    ),
                  ),
                const SizedBox(height: 8),
                GestureDetector(
                  onTap: () => context.push('/risk'),
                  child: Text(
                    'View details →',
                    style: AppTypography.labelMd.copyWith(
                      color: AppColors.sunriseAmber,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSegmentRow(RouteSegment segment) {
    final color = _colorForRisk(segment.riskLevel);
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        children: [
          Container(
            width: 4,
            height: 40,
            decoration: BoxDecoration(
              color: color,
              borderRadius: BorderRadius.circular(2),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  segment.description ?? 'Route segment',
                  style: AppTypography.bodySm.copyWith(
                    color: AppColors.primaryText,
                  ),
                ),
                if (segment.weather != null)
                  Text(
                    '${segment.weather!.condition} • ${segment.weather!.precipitation.round()} mm/hr',
                    style: AppTypography.labelCaps.copyWith(
                      color: AppColors.onSurfaceVariant,
                    ),
                  ),
              ],
            ),
          ),
          RiskBadge(level: segment.riskLevel, showDot: false),
        ],
      ),
    );
  }

  Widget _buildHazardCard(BuildContext context, Hazard hazard) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: WeatherCard(
        onTap: () => context.push('/hazard'),
        padding: const EdgeInsets.all(16),
        child: Row(
          children: [
            Container(
              width: 40,
              height: 40,
              decoration: BoxDecoration(
                color: _colorForRisk(hazard.severity).withValues(alpha: 0.15),
                borderRadius: BorderRadius.circular(Radii.base),
              ),
              child: Icon(
                CupertinoIcons.exclamationmark_triangle,
                color: _colorForRisk(hazard.severity),
                size: 20,
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    hazard.title,
                    style: AppTypography.labelMd.copyWith(
                      color: AppColors.primaryText,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    hazard.source ?? '',
                    style: AppTypography.labelCaps.copyWith(
                      color: AppColors.onSurfaceVariant,
                    ),
                  ),
                ],
              ),
            ),
            RiskBadge(level: hazard.severity, showDot: false),
          ],
        ),
      ),
    );
  }

  Widget _buildRecommendationCard(BuildContext context, TripResponse trip) {
    return WeatherCard(
      backgroundColor: AppColors.primaryContainer,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(CupertinoIcons.lightbulb_fill,
                  color: AppColors.sunriseAmber, size: 20),
              const SizedBox(width: 8),
              Text(
                'Recommendation',
                style: AppTypography.headlineMd.copyWith(
                  color: AppColors.onPrimary,
                ),
              ),
            ],
          ),
          const SizedBox(height: Spacing.stackSm),
          Text(
            trip.recommendation?.headline ?? (trip.status == TripStatus.routingUnavailable ? 'Routing Unavailable' : 'Recommendation Unavailable'),
            style: AppTypography.bodyMd.copyWith(
              color: AppColors.surfaceContainerHighest,
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            trip.recommendation?.body ?? 'No recommendation is available at this time.',
            style: AppTypography.bodySm.copyWith(
              color: AppColors.onPrimaryContainer,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildActionButtons(BuildContext context) {
    return Row(
      children: [
        Expanded(
          child: _ActionButton(
            icon: CupertinoIcons.slider_horizontal_3,
            label: 'What-If',
            onTap: () => context.push('/what-if'),
          ),
        ),
        const SizedBox(width: Spacing.gutter),
        Expanded(
          child: _ActionButton(
            icon: CupertinoIcons.arrow_right_arrow_left,
            label: 'Compare',
            onTap: () => context.push('/mode-comparison'),
          ),
        ),
      ],
    );
  }

  Color _colorForRisk(RiskLevel level) => switch (level) {
    RiskLevel.low => AppColors.riskLow,
    RiskLevel.moderate => AppColors.riskModerate,
    RiskLevel.high => AppColors.riskHigh,
    RiskLevel.severe => AppColors.riskSevere,
  };

  String _modeLabel(TransportMode mode) => switch (mode) {
    TransportMode.bike => 'Two-wheeler',
    TransportMode.car => 'Car',
    TransportMode.metro => 'Metro',
    TransportMode.walk => 'Walk',
  };
}

// ── Route Map with risk-colored segments ──

class _RouteMap extends StatelessWidget {
  final List<RouteSegment> segments;
  final List<Hazard> hazards;

  const _RouteMap({required this.segments, required this.hazards});

  @override
  Widget build(BuildContext context) {
    final allPoints = <LatLng>[];
    final polylines = <Polyline>[];

    for (final seg in segments) {
      final start = LatLng(seg.startLat, seg.startLng);
      final end = LatLng(seg.endLat, seg.endLng);
      allPoints.addAll([start, end]);

      polylines.add(Polyline(
        points: [start, end],
        color: _colorForRisk(seg.riskLevel),
        strokeWidth: 5,
        strokeCap: StrokeCap.round,
      ));
    }

    final bounds = LatLngBounds.fromPoints(allPoints);

    final hazardMarkers = hazards.map((h) => Marker(
          point: LatLng(h.lat, h.lng),
          width: 32,
          height: 32,
          child: Container(
            decoration: BoxDecoration(
              color: AppColors.riskSevere,
              shape: BoxShape.circle,
              border: Border.all(color: Colors.white, width: 2),
            ),
            child: const Icon(
              CupertinoIcons.exclamationmark_triangle_fill,
              color: Colors.white,
              size: 16,
            ),
          ),
        )).toList();

    return FlutterMap(
      options: MapOptions(
        initialCameraFit: CameraFit.bounds(
          bounds: bounds,
          padding: const EdgeInsets.all(48),
        ),
        interactionOptions: const InteractionOptions(
          flags: InteractiveFlag.pinchZoom | InteractiveFlag.drag,
        ),
      ),
      children: [
        TileLayer(
          urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
          userAgentPackageName: 'com.weathergpt.weather_gpt',
          tileBuilder: _lightMapTileBuilder,
        ),
        PolylineLayer(polylines: polylines),
        MarkerLayer(markers: hazardMarkers),
      ],
    );
  }

  /// Custom tile builder to achieve the muted/cream map style per Stitch
  Widget _lightMapTileBuilder(
    BuildContext context,
    Widget tileWidget,
    TileImage tile,
  ) {
    return ColorFiltered(
      colorFilter: const ColorFilter.matrix(<double>[
        0.95, 0.05, 0.00, 0, 10,
        0.02, 0.90, 0.05, 0, 10,
        0.02, 0.05, 0.85, 0, 10,
        0.00, 0.00, 0.00, 1, 0,
      ]),
      child: tileWidget,
    );
  }

  Color _colorForRisk(RiskLevel level) => switch (level) {
    RiskLevel.low => AppColors.riskLow,
    RiskLevel.moderate => AppColors.sunriseAmber,
    RiskLevel.high => AppColors.riskHigh,
    RiskLevel.severe => AppColors.riskSevere,
  };
}

class _CircleButton extends StatelessWidget {
  final IconData icon;
  final VoidCallback onTap;

  const _CircleButton({required this.icon, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: 40,
        height: 40,
        decoration: BoxDecoration(
          color: AppColors.cardBackground.withValues(alpha: 0.9),
          shape: BoxShape.circle,
          boxShadow: const [
            BoxShadow(
              offset: Offset(0, 2),
              blurRadius: 8,
              color: AppColors.softShadow,
            ),
          ],
        ),
        child: Icon(icon, size: 20, color: AppColors.primaryText),
      ),
    );
  }
}

class _ActionButton extends StatelessWidget {
  final IconData icon;
  final String label;
  final VoidCallback onTap;

  const _ActionButton({
    required this.icon,
    required this.label,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 14),
        decoration: BoxDecoration(
          color: AppColors.primaryContainer,
          borderRadius: BorderRadius.circular(Radii.full),
        ),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(icon, color: AppColors.onPrimary, size: 18),
            const SizedBox(width: 8),
            Text(
              label,
              style: AppTypography.buttonLabel.copyWith(
                color: AppColors.onPrimary,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
