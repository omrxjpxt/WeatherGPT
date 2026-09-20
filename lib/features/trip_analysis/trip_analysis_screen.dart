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
import '../profile/auth_dialog.dart';

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

class _TripAnalysisBody extends ConsumerStatefulWidget {
  final TripResponse trip;

  const _TripAnalysisBody({required this.trip});

  @override
  ConsumerState<_TripAnalysisBody> createState() => _TripAnalysisBodyState();
}

class _TripAnalysisBodyState extends ConsumerState<_TripAnalysisBody> {
  late String _activeRouteId;

  @override
  void initState() {
    super.initState();
    _initActiveRouteId();
  }

  @override
  void didUpdateWidget(covariant _TripAnalysisBody oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.trip != widget.trip) {
      _initActiveRouteId();
    }
  }

  void _initActiveRouteId() {
    final selected = widget.trip.routes.where((r) => r.evaluation.isSelected).firstOrNull;
    _activeRouteId = selected?.routeId ?? widget.trip.routes.firstOrNull?.routeId ?? '';
  }

  EvaluatedRoute? get _activeRoute =>
      widget.trip.routes.where((r) => r.routeId == _activeRouteId).firstOrNull;

  @override
  Widget build(BuildContext context) {
    final active = _activeRoute;
    final displaySegments = (active != null && active.segments.isNotEmpty)
        ? active.segments
        : widget.trip.route;
    final displayHazards = (active != null && active.hazards.isNotEmpty)
        ? active.hazards
        : widget.trip.hazards;
    final displayTraffic = active?.traffic ?? widget.trip.traffic;
    final displayDistance = active?.distanceKm ?? widget.trip.distanceKm;
    final displayDuration = active?.evaluation.trafficAwareDuration ??
        (widget.trip.traffic != null && widget.trip.traffic!.status != TrafficStatus.unavailable
            ? widget.trip.traffic!.trafficAwareDuration
            : widget.trip.estimatedDuration);
    final displayRisk = active?.risk ?? widget.trip.risk;

    return CustomScrollView(
      slivers: [
        // ── Map Section ──
        SliverToBoxAdapter(
          child: SizedBox(
            height: 320,
            child: Stack(
              children: [
                _RouteMap(segments: displaySegments, hazards: displayHazards),
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
                                '${widget.trip.request.origin} → ${widget.trip.request.destination}',
                                style: AppTypography.labelMd.copyWith(
                                  color: AppColors.primaryText,
                                  fontWeight: FontWeight.w600,
                                ),
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                              ),
                              const SizedBox(height: 4),
                              Text(
                                '$displayDistance km • ${displayDuration.inMinutes} min • ${_modeLabel(widget.trip.request.mode)}',
                                style: AppTypography.bodySm.copyWith(
                                  color: AppColors.onSurfaceVariant,
                                ),
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                              ),
                            ],
                          ),
                        ),
                        if (displayRisk != null) ...[
                          const SizedBox(width: 12),
                          RiskBadge(level: displayRisk.level),
                        ],
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
              _buildRiskCard(context, widget.trip, displayRisk),
              const SizedBox(height: Spacing.stackMd),

              // Traffic conditions card
              _buildTrafficCard(
                context,
                widget.trip,
                displayTraffic,
                active?.staticDuration ?? widget.trip.estimatedDuration,
              ),
              const SizedBox(height: Spacing.stackMd),

              // Air Quality intelligence card
              _buildAirQualityCard(
                context,
                widget.trip.airQuality,
                widget.trip.request.mode,
              ),
              const SizedBox(height: Spacing.stackLg),

              // Route Alternatives
              if (widget.trip.routes.length > 1) ...[
                _buildRouteAlternativesSection(context),
              ],

              // Route segments
              const SectionTitle(title: 'Route Segments'),
              const SizedBox(height: Spacing.stackSm),
              if (displaySegments.isEmpty)
                Padding(
                  padding: const EdgeInsets.symmetric(vertical: 8),
                  child: Text(
                    widget.trip.status == TripStatus.routingUnavailable
                        ? 'Routing is currently unavailable.'
                        : 'No route segments available.',
                    style: AppTypography.bodySm.copyWith(
                      color: AppColors.onSurfaceVariant,
                    ),
                  ),
                )
              else
                ...displaySegments.map((seg) => _buildSegmentRow(seg)),
              const SizedBox(height: Spacing.stackLg),

              // Hazards
              if (displayHazards.isNotEmpty) ...[
                const SectionTitle(title: 'Hazards'),
                const SizedBox(height: Spacing.stackSm),
                ...displayHazards.map((h) => _buildHazardCard(context, h)),
                const SizedBox(height: Spacing.stackLg),
              ],

              // Recommendation
              _buildRecommendationCard(context, widget.trip),
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

  Widget _buildRouteAlternativesSection(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const SectionTitle(title: 'Route Alternatives'),
        const SizedBox(height: Spacing.stackSm),
        ...widget.trip.routes.map((route) => _buildRouteCard(context, route)),
        const SizedBox(height: Spacing.stackLg),
      ],
    );
  }

  Widget _buildRouteCard(BuildContext context, EvaluatedRoute route) {
    final isInspected = route.routeId == _activeRouteId;
    final isRecommended = route.evaluation.isSelected;
    final delayMins = (route.evaluation.trafficDelaySeconds / 60).round();
    final delayStr = delayMins > 0 ? ' (+${delayMins}m traffic)' : '';

    return Padding(
      padding: const EdgeInsets.only(bottom: Spacing.stackSm),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          key: Key('route_card_${route.routeId}'),
          onTap: () {
            setState(() {
              _activeRouteId = route.routeId;
            });
          },
          borderRadius: BorderRadius.circular(Radii.card),
          child: Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: isInspected ? AppColors.surfaceContainerLow : AppColors.cardBackground,
              borderRadius: BorderRadius.circular(Radii.card),
              border: Border.all(
                color: isInspected
                    ? AppColors.sunriseAmber
                    : (isRecommended ? AppColors.cardBorderWarm : AppColors.cardBorderCool),
                width: isInspected ? 2.0 : 1.0,
              ),
              boxShadow: const [
                BoxShadow(
                  offset: Offset(0, 2),
                  blurRadius: 8,
                  color: AppColors.softShadow,
                ),
              ],
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Wrap(
                            spacing: 6,
                            runSpacing: 4,
                            crossAxisAlignment: WrapCrossAlignment.center,
                            children: [
                              Text(
                                route.summary.isNotEmpty ? route.summary : 'Route ${route.routeId}',
                                style: AppTypography.labelMd.copyWith(
                                  fontWeight: FontWeight.w600,
                                  color: AppColors.primaryText,
                                ),
                              ),
                              if (isRecommended) ...[
                                Container(
                                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                  decoration: BoxDecoration(
                                    color: AppColors.riskLowBg,
                                    borderRadius: BorderRadius.circular(Radii.badge),
                                    border: Border.all(color: AppColors.riskLow.withValues(alpha: 0.3)),
                                  ),
                                  child: Text(
                                    'RECOMMENDED',
                                    style: AppTypography.labelCaps.copyWith(
                                      color: AppColors.riskLow,
                                      fontWeight: FontWeight.bold,
                                      fontSize: 10,
                                      letterSpacing: 0.5,
                                    ),
                                  ),
                                ),
                              ],
                              if (isInspected) ...[
                                Container(
                                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                  decoration: BoxDecoration(
                                    color: AppColors.sunriseAmber.withValues(alpha: 0.15),
                                    borderRadius: BorderRadius.circular(Radii.badge),
                                  ),
                                  child: Text(
                                    'VIEWING',
                                    style: AppTypography.labelCaps.copyWith(
                                      color: AppColors.secondary,
                                      fontWeight: FontWeight.bold,
                                      fontSize: 10,
                                      letterSpacing: 0.5,
                                    ),
                                  ),
                                ),
                              ],
                            ],
                          ),
                          const SizedBox(height: 4),
                          Text(
                            '${route.distanceKm} km • ${route.evaluation.trafficAwareDuration.inMinutes} min$delayStr',
                            style: AppTypography.bodySm.copyWith(
                              color: AppColors.onSurfaceVariant,
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(width: 8),
                    RiskBadge(level: route.evaluation.riskLevel),
                  ],
                ),
                if (route.evaluation.selectionReason != null && route.evaluation.selectionReason!.isNotEmpty) ...[
                  const SizedBox(height: 8),
                  Text(
                    route.evaluation.selectionReason!,
                    style: AppTypography.bodySm.copyWith(
                      fontSize: 12,
                      color: isRecommended ? AppColors.primaryText : AppColors.onSurfaceVariant,
                      fontStyle: FontStyle.italic,
                    ),
                  ),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildRiskCard(BuildContext context, TripResponse trip, [RiskAssessment? overrideRisk]) {
    final risk = overrideRisk ?? trip.risk;
    return WeatherCard(
      child: Row(
        children: [
          if (risk != null) ...[
            RiskScoreIndicator(
              score: risk.overallScore,
              level: risk.level,
            ),
            const SizedBox(width: Spacing.md),
          ],
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                if (risk != null) RiskBadge(level: risk.level),
                const SizedBox(height: 8),
                if (risk != null)
                  Text(
                    risk.summary,
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

  Widget _buildTrafficCard(
    BuildContext context,
    TripResponse trip, [
    TrafficSnapshot? overrideTraffic,
    Duration? overrideStaticDuration,
  ]) {
    final traffic = overrideTraffic ?? trip.traffic;
    final staticDuration = overrideStaticDuration ?? trip.estimatedDuration;
    final isAvailable = traffic != null && traffic.status != TrafficStatus.unavailable;

    if (!isAvailable) {
      return WeatherCard(
        backgroundColor: AppColors.surfaceContainerLow,
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: AppColors.surfaceContainerHigh,
                borderRadius: BorderRadius.circular(Radii.base),
              ),
              child: const Icon(
                CupertinoIcons.car_detailed,
                color: AppColors.onSurfaceVariant,
                size: 20,
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Traffic Data Unavailable',
                    style: AppTypography.labelMd.copyWith(
                      color: AppColors.primaryText,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    'Trip evaluated using base routing (${staticDuration.inMinutes} min static duration). No traffic delay applied.',
                    style: AppTypography.bodySm.copyWith(
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

    final delayMins = traffic.trafficDelay.inMinutes;
    final delayText = delayMins > 0 ? '+$delayMins min' : 'No delay';
    final delayColor = delayMins > 10
        ? AppColors.riskHigh
        : (delayMins > 0 ? AppColors.sunriseAmber : AppColors.riskLow);

    return WeatherCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: delayColor.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(Radii.base),
                ),
                child: Icon(
                  CupertinoIcons.car_detailed,
                  color: delayColor,
                  size: 20,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'TRAFFIC CONDITIONS',
                      style: AppTypography.labelCaps.copyWith(
                        color: AppColors.onSurfaceVariant,
                      ),
                    ),
                    Text(
                      _congestionLabel(traffic.congestionLevel),
                      style: AppTypography.headlineMd.copyWith(
                        color: AppColors.primaryText,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ],
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(
                  color: delayColor.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(Radii.full),
                  border: Border.all(color: delayColor.withValues(alpha: 0.3)),
                ),
                child: Text(
                  delayText,
                  style: AppTypography.labelMd.copyWith(
                    color: delayColor,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: Spacing.stackMd),
          const Divider(),
          const SizedBox(height: Spacing.stackSm),

          // Duration metrics: static vs traffic-aware vs delay
          Row(
            children: [
              Expanded(
                child: _TrafficMetric(
                  label: 'CURRENT TIME',
                  value: '${traffic.trafficAwareDuration.inMinutes} min',
                  color: AppColors.primaryText,
                ),
              ),
              Expanded(
                child: _TrafficMetric(
                  label: 'FREE-FLOW',
                  value: '${traffic.staticDuration.inMinutes} min',
                  color: AppColors.onSurfaceVariant,
                ),
              ),
              Expanded(
                child: _TrafficMetric(
                  label: 'EST. DELAY',
                  value: delayText,
                  color: delayColor,
                ),
              ),
            ],
          ),

          if (traffic.currentSpeedKmh != null && traffic.freeFlowSpeedKmh != null) ...[
            const SizedBox(height: Spacing.stackSm),
            Text(
              'Avg Speed: ${traffic.currentSpeedKmh!.round()} km/h (free-flow: ${traffic.freeFlowSpeedKmh!.round()} km/h)',
              style: AppTypography.bodySm.copyWith(
                color: AppColors.onSurfaceVariant,
              ),
            ),
          ],

          const SizedBox(height: Spacing.stackSm),
          Text(
            'Source: ${traffic.sourceName} • ${traffic.provenance}',
            style: AppTypography.labelCaps.copyWith(
              color: AppColors.outline,
            ),
          ),
        ],
      ),
    );
  }

  String _congestionLabel(CongestionLevel level) => switch (level) {
    CongestionLevel.freeFlow => 'Free Flow',
    CongestionLevel.moderate => 'Moderate Traffic',
    CongestionLevel.heavy => 'Heavy Congestion',
    CongestionLevel.severe => 'Severe Congestion',
    CongestionLevel.unknown => 'Unknown Conditions',
  };

  Widget _buildAirQualityCard(
    BuildContext context,
    AirQualitySnapshot? aqi,
    TransportMode mode,
  ) {
    final isAvailable = aqi != null && aqi.isAvailable && aqi.aqi >= 0;

    if (!isAvailable) {
      return WeatherCard(
        key: const Key('air_quality_card_unavailable'),
        backgroundColor: AppColors.surfaceContainerLow,
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: AppColors.surfaceContainerHigh,
                borderRadius: BorderRadius.circular(Radii.base),
              ),
              child: const Icon(
                CupertinoIcons.wind,
                color: AppColors.onSurfaceVariant,
                size: 20,
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Air Quality Unavailable',
                    style: AppTypography.labelMd.copyWith(
                      color: AppColors.primaryText,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    'Real-time atmospheric CAMS data unavailable. Baseline environmental model applied.',
                    style: AppTypography.bodySm.copyWith(
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

    final catLower = aqi.category.toLowerCase();
    final Color aqiColor;
    final Color aqiBgColor;
    if (catLower.contains('good')) {
      aqiColor = AppColors.riskLow;
      aqiBgColor = AppColors.riskLowBg;
    } else if (catLower.contains('moderate') || catLower.contains('satisfactory')) {
      aqiColor = AppColors.sunriseAmber;
      aqiBgColor = AppColors.riskModerateBg;
    } else if (catLower.contains('poor') || catLower.contains('unhealthy')) {
      aqiColor = AppColors.riskHigh;
      aqiBgColor = AppColors.riskHighBg;
    } else {
      aqiColor = AppColors.riskSevere;
      aqiBgColor = AppColors.riskSevereBg;
    }

    final String modeGuidance;
    switch (mode) {
      case TransportMode.car:
        modeGuidance = 'Cabin air-filtration active. Exposure reduced inside enclosed vehicle.';
        break;
      case TransportMode.metro:
        modeGuidance = 'Enclosed transit. High cabin protection with minimal atmospheric exposure.';
        break;
      case TransportMode.bike:
      case TransportMode.walk:
        if (aqi.aqi >= 200 || catLower.contains('poor') || catLower.contains('severe')) {
          modeGuidance = 'High direct exposure. N95 mask strongly recommended for outdoor travel.';
        } else if (aqi.aqi >= 100) {
          modeGuidance = 'Moderate outdoor exposure. Consider protective mask if sensitive to pollution.';
        } else {
          modeGuidance = 'Direct outdoor exposure. Air quality within acceptable limits.';
        }
        break;
    }

    return WeatherCard(
      key: const Key('air_quality_card'),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: aqiColor.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(Radii.base),
                ),
                child: Icon(
                  CupertinoIcons.wind,
                  color: aqiColor,
                  size: 20,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'AIR QUALITY INTELLIGENCE',
                      style: AppTypography.labelCaps.copyWith(
                        color: AppColors.onSurfaceVariant,
                      ),
                    ),
                    Text(
                      'AQI ${aqi.aqi.round()} • ${aqi.category}',
                      style: AppTypography.headlineMd.copyWith(
                        color: AppColors.primaryText,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ],
                ),
              ),
              if (aqi.isStale)
                Container(
                  key: const Key('air_quality_stale_indicator'),
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: AppColors.surfaceContainerHigh,
                    borderRadius: BorderRadius.circular(Radii.full),
                    border: Border.all(color: AppColors.outlineVariant),
                  ),
                  child: Text(
                    'STALE DATA',
                    style: AppTypography.labelCaps.copyWith(
                      color: AppColors.onSurfaceVariant,
                      fontWeight: FontWeight.bold,
                      fontSize: 10,
                    ),
                  ),
                )
              else
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(
                    color: aqiBgColor,
                    borderRadius: BorderRadius.circular(Radii.full),
                    border: Border.all(color: aqiColor.withValues(alpha: 0.3)),
                  ),
                  child: Text(
                    aqi.category.toUpperCase(),
                    style: AppTypography.labelCaps.copyWith(
                      color: aqiColor,
                      fontWeight: FontWeight.w700,
                      fontSize: 10,
                    ),
                  ),
                ),
            ],
          ),
          const SizedBox(height: Spacing.stackMd),
          const Divider(),
          const SizedBox(height: Spacing.stackSm),

          // Metrics row: AQI, PM2.5, PM10
          Row(
            children: [
              Expanded(
                child: _TrafficMetric(
                  label: 'AQI INDEX',
                  value: '${aqi.aqi.round()}',
                  color: aqiColor,
                ),
              ),
              Expanded(
                child: _TrafficMetric(
                  label: 'PM2.5',
                  value: '${aqi.pm25.toStringAsFixed(1)} µg/m³',
                  color: AppColors.primaryText,
                ),
              ),
              if (aqi.pm10 != null)
                Expanded(
                  child: _TrafficMetric(
                    label: 'PM10',
                    value: '${aqi.pm10!.toStringAsFixed(1)} µg/m³',
                    color: AppColors.onSurfaceVariant,
                  ),
                ),
            ],
          ),
          const SizedBox(height: Spacing.stackSm),

          // Mode-specific exposure guidance
          Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: AppColors.surfaceContainerLow,
              borderRadius: BorderRadius.circular(Radii.base),
              border: Border.all(color: AppColors.outlineVariant.withValues(alpha: 0.5)),
            ),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Icon(
                  mode == TransportMode.car || mode == TransportMode.metro
                      ? CupertinoIcons.shield_fill
                      : CupertinoIcons.exclamationmark_triangle_fill,
                  size: 16,
                  color: mode == TransportMode.car || mode == TransportMode.metro
                      ? AppColors.riskLow
                      : (aqi.aqi >= 100 ? AppColors.sunriseAmber : AppColors.riskLow),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    modeGuidance,
                    style: AppTypography.bodySm.copyWith(
                      color: AppColors.primaryText,
                    ),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: Spacing.stackSm),
          Text(
            'Source: ${aqi.sourceName} • ${aqi.provenance}',
            style: AppTypography.labelCaps.copyWith(
              color: AppColors.outline,
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
              Expanded(
                child: Text(
                  'Recommendation',
                  style: AppTypography.headlineMd.copyWith(
                    color: AppColors.onPrimary,
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
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
            icon: CupertinoIcons.bookmark,
            label: 'Save Route',
            onTap: () => _handleSaveRoute(context),
          ),
        ),
        const SizedBox(width: Spacing.sm),
        Expanded(
          child: _ActionButton(
            icon: CupertinoIcons.slider_horizontal_3,
            label: 'What-If',
            onTap: () => context.push('/what-if'),
          ),
        ),
        const SizedBox(width: Spacing.sm),
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

  Future<void> _handleSaveRoute(BuildContext context) async {
    final authState = ref.read(authStateProvider);

    if (!authState.isAuthenticated) {
      showDialog<void>(
        context: context,
        builder: (ctx) => AlertDialog(
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(Radii.card)),
          backgroundColor: AppColors.cardBackground,
          title: Text(
            'Save Route',
            style: AppTypography.headlineMd.copyWith(color: AppColors.primaryText),
          ),
          content: Text(
            'Sign in to save this route to your profile and sync across devices.',
            style: AppTypography.bodySm.copyWith(color: AppColors.onSurfaceVariant),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(ctx).pop(),
              child: Text(
                'Continue as Guest',
                style: AppTypography.labelMd.copyWith(color: AppColors.outline),
              ),
            ),
            ElevatedButton(
              onPressed: () {
                Navigator.of(ctx).pop();
                AuthDialog.show(
                  context,
                  title: 'Sign In to Save Route',
                  subtitle: 'Bookmark your commutes and access them anytime.',
                );
              },
              style: ElevatedButton.styleFrom(
                backgroundColor: AppColors.sunriseAmber,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(Radii.base)),
              ),
              child: Text(
                'Sign In / Create Account',
                style: AppTypography.labelMd.copyWith(color: Colors.white, fontWeight: FontWeight.bold),
              ),
            ),
          ],
        ),
      );
      return;
    }

    try {
      final origin = widget.trip.request.origin;
      final destination = widget.trip.request.destination;
      final routeId = 'route_${origin.hashCode.abs()}_${destination.hashCode.abs()}';
      final savedRoute = SavedRoute(
        id: routeId,
        name: '$origin → $destination',
        originId: origin,
        destinationId: destination,
        createdAt: DateTime.now(),
      );

      await ref.read(userSavedRoutesProvider.notifier).saveRoute(savedRoute);

      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              'Route saved to your profile',
              style: AppTypography.bodySm.copyWith(color: Colors.white),
            ),
            backgroundColor: AppColors.primaryText,
            duration: const Duration(seconds: 3),
            behavior: SnackBarBehavior.floating,
          ),
        );
      }
    } catch (e) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              'Failed to save route: $e',
              style: AppTypography.bodySm.copyWith(color: Colors.white),
            ),
            backgroundColor: AppColors.riskSevere,
          ),
        );
      }
    }
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

    final bounds = allPoints.isNotEmpty ? LatLngBounds.fromPoints(allPoints) : null;

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
        initialCenter: const LatLng(28.6139, 77.2090),
        initialZoom: 11,
        initialCameraFit: bounds != null
            ? CameraFit.bounds(
                bounds: bounds,
                padding: const EdgeInsets.all(48),
              )
            : null,
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
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, color: AppColors.onPrimary, size: 18),
            const SizedBox(width: 8),
            Flexible(
              child: Text(
                label,
                style: AppTypography.buttonLabel.copyWith(
                  color: AppColors.onPrimary,
                ),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _TrafficMetric extends StatelessWidget {
  final String label;
  final String value;
  final Color color;

  const _TrafficMetric({
    required this.label,
    required this.value,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: AppTypography.labelCaps.copyWith(
            color: AppColors.onSurfaceVariant,
            fontSize: 10,
          ),
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
        ),
        const SizedBox(height: 2),
        Text(
          value,
          style: AppTypography.labelMd.copyWith(
            color: color,
            fontWeight: FontWeight.w700,
          ),
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
        ),
      ],
    );
  }
}
