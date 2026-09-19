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
import 'auth_dialog.dart';

/// Profile / Settings screen with dynamic authentication and user data persistence
class ProfileScreen extends ConsumerWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final authState = ref.watch(authStateProvider);
    final userProfileAsync = ref.watch(userProfileProvider);
    final savedRoutesAsync = ref.watch(userSavedRoutesProvider);
    final tripHistoryAsync = ref.watch(userTripHistoryProvider);

    return Scaffold(
      backgroundColor: AppColors.warmIvory,
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: Spacing.pagePadding),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const SizedBox(height: Spacing.lg),
              Text(
                'Profile',
                style: AppTypography.headlineLgMobile.copyWith(
                  color: AppColors.primaryText,
                ),
              ),
              const SizedBox(height: Spacing.stackLg),

              // ── User Identity Card ──
              if (authState.isAuthenticated) ...[
                _buildAuthenticatedCard(context, ref, authState.user!, userProfileAsync.asData?.value),
              ] else ...[
                _buildGuestCard(context),
              ],
              const SizedBox(height: Spacing.stackLg),

              // ── Saved Routes ──
              const SectionTitle(title: 'Saved Routes'),
              const SizedBox(height: Spacing.stackMd),
              if (!authState.isAuthenticated) ...[
                _buildGuestFeatureCard(
                  context,
                  icon: CupertinoIcons.location,
                  message: 'Sign in to access and manage your saved commutes across devices.',
                ),
              ] else ...[
                savedRoutesAsync.when(
                  data: (routes) {
                    if (routes.isEmpty) {
                      return WeatherCard(
                        padding: const EdgeInsets.all(16),
                        child: Text(
                          'No saved routes yet. Use "Save Route" on any trip analysis to bookmark it.',
                          style: AppTypography.bodySm.copyWith(
                            color: AppColors.onSurfaceVariant,
                            fontStyle: FontStyle.italic,
                          ),
                        ),
                      );
                    }
                    return Column(
                      children: routes.map((route) => _buildSavedRouteCard(context, ref, route)).toList(),
                    );
                  },
                  loading: () => const Center(
                    child: Padding(
                      padding: EdgeInsets.all(16),
                      child: CircularProgressIndicator(color: AppColors.sunriseAmber, strokeWidth: 2),
                    ),
                  ),
                  error: (e, _) => WeatherCard(
                    padding: const EdgeInsets.all(16),
                    child: Text('Unable to load saved routes: $e', style: AppTypography.bodySm),
                  ),
                ),
              ],
              const SizedBox(height: Spacing.stackLg),

              // ── Trip History (Snapshots for Audit) ──
              const SectionTitle(title: 'Trip History'),
              const SizedBox(height: Spacing.stackMd),
              if (!authState.isAuthenticated) ...[
                _buildGuestFeatureCard(
                  context,
                  icon: CupertinoIcons.clock,
                  message: 'Sign in to view your past trip analyses and historical snapshots.',
                ),
              ] else ...[
                tripHistoryAsync.when(
                  data: (history) {
                    if (history.isEmpty) {
                      return WeatherCard(
                        padding: const EdgeInsets.all(16),
                        child: Text(
                          'No past trip analyses found. Analyzed trips will appear here.',
                          style: AppTypography.bodySm.copyWith(
                            color: AppColors.onSurfaceVariant,
                            fontStyle: FontStyle.italic,
                          ),
                        ),
                      );
                    }
                    return Column(
                      children: history.map((item) => _buildTripHistoryCard(context, item)).toList(),
                    );
                  },
                  loading: () => const Center(
                    child: Padding(
                      padding: EdgeInsets.all(16),
                      child: CircularProgressIndicator(color: AppColors.sunriseAmber, strokeWidth: 2),
                    ),
                  ),
                  error: (e, _) => WeatherCard(
                    padding: const EdgeInsets.all(16),
                    child: Text('Unable to load trip history: $e', style: AppTypography.bodySm),
                  ),
                ),
              ],
              const SizedBox(height: Spacing.stackLg),

              // ── Preferences ──
              const SectionTitle(title: 'Preferences'),
              const SizedBox(height: Spacing.stackMd),
              _SettingsCard(
                icon: Icons.two_wheeler,
                title: 'Default Transport',
                subtitle: 'Two-wheeler',
              ),
              const SizedBox(height: Spacing.stackSm),
              _SettingsCard(
                icon: CupertinoIcons.bell,
                title: 'Alert Notifications',
                subtitle: 'Enabled for Delhi-NCR',
              ),
              const SizedBox(height: Spacing.stackSm),
              _SettingsCard(
                icon: CupertinoIcons.globe,
                title: 'Language',
                subtitle: 'English + Hindi voice',
              ),
              const SizedBox(height: Spacing.stackLg),

              // ── Data & Privacy ──
              const SectionTitle(title: 'Data & Privacy'),
              const SizedBox(height: Spacing.stackMd),
              _SettingsCard(
                icon: CupertinoIcons.doc_text,
                title: 'Data Sources',
                subtitle: 'IMD, NDMA, Google Traffic',
              ),
              const SizedBox(height: Spacing.stackSm),
              _SettingsCard(
                icon: CupertinoIcons.shield,
                title: 'Privacy Policy',
                subtitle: 'How we handle your data',
              ),
              const SizedBox(height: Spacing.stackLg),

              // ── Sign Out Action (when authenticated) ──
              if (authState.isAuthenticated) ...[
                WeatherCard(
                  padding: const EdgeInsets.all(16),
                  child: InkWell(
                    onTap: () => ref.read(authStateProvider.notifier).signOut(),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        const Icon(CupertinoIcons.square_arrow_left, color: AppColors.riskSevere, size: 20),
                        const SizedBox(width: 8),
                        Text(
                          'Sign Out',
                          style: AppTypography.labelMd.copyWith(
                            color: AppColors.riskSevere,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: Spacing.stackLg),
              ],

              // ── Version ──
              Center(
                child: Text(
                  'WeatherGPT v0.1.0 • Powered by AI',
                  style: AppTypography.labelCaps.copyWith(
                    color: AppColors.outline,
                  ),
                ),
              ),
              const SizedBox(height: Spacing.sectionMargin),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildGuestCard(BuildContext context) {
    return WeatherCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 52,
                height: 52,
                decoration: BoxDecoration(
                  color: AppColors.sunriseAmber.withValues(alpha: 0.15),
                  shape: BoxShape.circle,
                ),
                child: const Icon(CupertinoIcons.person_crop_circle_badge_exclam,
                    color: AppColors.sunriseAmber, size: 28),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Guest Traveler',
                      style: AppTypography.headlineMd.copyWith(
                        color: AppColors.primaryText,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      'Free trip analysis mode',
                      style: AppTypography.bodySm.copyWith(
                        color: AppColors.onSurfaceVariant,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),
          Text(
            'Sign in to bookmark favorite routes, view historical trip audits, and synchronize across devices.',
            style: AppTypography.bodySm.copyWith(
              color: AppColors.onSurfaceVariant,
            ),
          ),
          const SizedBox(height: 12),
          SizedBox(
            width: double.infinity,
            child: ElevatedButton(
              onPressed: () => AuthDialog.show(context),
              style: ElevatedButton.styleFrom(
                backgroundColor: AppColors.sunriseAmber,
                foregroundColor: Colors.white,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(Radii.base)),
                padding: const EdgeInsets.symmetric(vertical: 12),
                elevation: 0,
              ),
              child: Text(
                'Sign In / Create Account',
                style: AppTypography.labelMd.copyWith(
                  color: Colors.white,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildAuthenticatedCard(
    BuildContext context,
    WidgetRef ref,
    dynamic user,
    UserProfile? profile,
  ) {
    final displayName = profile?.displayName ?? user.displayName ?? 'Traveler';
    final email = profile?.email ?? user.email ?? 'Authenticated Account';

    return WeatherCard(
      child: Row(
        children: [
          Container(
            width: 56,
            height: 56,
            decoration: BoxDecoration(
              color: AppColors.sunriseAmber.withValues(alpha: 0.15),
              shape: BoxShape.circle,
            ),
            child: Center(
              child: Text(
                displayName.isNotEmpty ? displayName[0].toUpperCase() : 'T',
                style: AppTypography.headlineMd.copyWith(
                  color: AppColors.sunriseAmber,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  displayName,
                  style: AppTypography.headlineMd.copyWith(
                    color: AppColors.primaryText,
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
                const SizedBox(height: 2),
                Text(
                  email,
                  style: AppTypography.bodySm.copyWith(
                    color: AppColors.onSurfaceVariant,
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
                const SizedBox(height: 4),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                  decoration: BoxDecoration(
                    color: AppColors.surfaceContainerHigh,
                    borderRadius: BorderRadius.circular(Radii.badge),
                  ),
                  child: Text(
                    'UID: ${user.uid.length > 12 ? user.uid.substring(0, 12) : user.uid}',
                    style: AppTypography.labelCaps.copyWith(
                      color: AppColors.outline,
                      fontSize: 10,
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

  Widget _buildGuestFeatureCard(
    BuildContext context, {
    required IconData icon,
    required String message,
  }) {
    return WeatherCard(
      padding: const EdgeInsets.all(16),
      child: Row(
        children: [
          Container(
            width: 36,
            height: 36,
            decoration: BoxDecoration(
              color: AppColors.surfaceContainerHigh,
              borderRadius: BorderRadius.circular(Radii.base),
            ),
            child: Icon(icon, color: AppColors.outline, size: 18),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              message,
              style: AppTypography.bodySm.copyWith(
                color: AppColors.onSurfaceVariant,
              ),
            ),
          ),
          const SizedBox(width: 8),
          GestureDetector(
            onTap: () => AuthDialog.show(context),
            child: Text(
              'Sign In',
              style: AppTypography.labelMd.copyWith(
                color: AppColors.sunriseAmber,
                fontWeight: FontWeight.bold,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSavedRouteCard(BuildContext context, WidgetRef ref, SavedRoute route) {
    return Padding(
      padding: const EdgeInsets.only(bottom: Spacing.stackSm),
      child: WeatherCard(
        padding: const EdgeInsets.all(14),
        child: Row(
          children: [
            Container(
              width: 38,
              height: 38,
              decoration: BoxDecoration(
                color: AppColors.sunriseAmber.withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(Radii.base),
              ),
              child: const Icon(CupertinoIcons.map_pin_ellipse, color: AppColors.sunriseAmber, size: 20),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: GestureDetector(
                behavior: HitTestBehavior.opaque,
                onTap: () {
                  ref.read(activeTripRequestProvider.notifier).update(
                        TripRequest(
                          origin: route.originId,
                          destination: route.destinationId,
                          departureTime: DateTime.now().add(const Duration(minutes: 15)),
                          mode: TransportMode.bike,
                        ),
                      );
                  context.push('/trips');
                },
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      route.name,
                      style: AppTypography.labelMd.copyWith(
                        color: AppColors.primaryText,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      '${route.originId} → ${route.destinationId}',
                      style: AppTypography.bodySm.copyWith(
                        color: AppColors.onSurfaceVariant,
                      ),
                    ),
                  ],
                ),
              ),
            ),
            IconButton(
              icon: const Icon(CupertinoIcons.trash, size: 18, color: AppColors.outline),
              onPressed: () => ref.read(userSavedRoutesProvider.notifier).deleteRoute(route.id),
              tooltip: 'Delete saved route',
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildTripHistoryCard(BuildContext context, TripHistorySummary item) {
    final riskLevel = RiskLevel.fromString(item.riskLevel);
    return Padding(
      padding: const EdgeInsets.only(bottom: Spacing.stackSm),
      child: WeatherCard(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Expanded(
                  child: Text(
                    '${item.origin} → ${item.destination}',
                    style: AppTypography.labelMd.copyWith(
                      color: AppColors.primaryText,
                      fontWeight: FontWeight.w600,
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
                RiskBadge(level: riskLevel, showDot: false),
              ],
            ),
            const SizedBox(height: 4),
            if (item.recommendationHeadline != null) ...[
              Text(
                item.recommendationHeadline!,
                style: AppTypography.bodySm.copyWith(
                  color: AppColors.onSurfaceVariant,
                ),
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
              ),
              const SizedBox(height: 6),
            ],
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Expanded(
                  child: Text(
                    '${item.mode.toUpperCase()} • ${_formatDate(item.createdAt)}',
                    style: AppTypography.labelCaps.copyWith(
                      color: AppColors.outline,
                      fontSize: 10,
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
                const SizedBox(width: 8),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                  decoration: BoxDecoration(
                    color: AppColors.surfaceContainerHigh,
                    borderRadius: BorderRadius.circular(Radii.badge),
                  ),
                  child: Text(
                    'Historical Snapshot (Audit)',
                    style: AppTypography.labelCaps.copyWith(
                      color: AppColors.outline,
                      fontSize: 9,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  String _formatDate(DateTime dt) {
    return '${dt.day}/${dt.month}/${dt.year}';
  }
}

class _SettingsCard extends StatelessWidget {
  final IconData icon;
  final String title;
  final String subtitle;

  const _SettingsCard({
    required this.icon,
    required this.title,
    required this.subtitle,
  });

  @override
  Widget build(BuildContext context) {
    return WeatherCard(
      padding: const EdgeInsets.all(16),
      child: Row(
        children: [
          Container(
            width: 40,
            height: 40,
            decoration: BoxDecoration(
              color: AppColors.surfaceContainerHigh,
              borderRadius: BorderRadius.circular(Radii.base),
            ),
            child: Icon(icon, color: AppColors.primaryText, size: 20),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: AppTypography.labelMd.copyWith(
                    color: AppColors.primaryText,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                Text(
                  subtitle,
                  style: AppTypography.bodySm.copyWith(
                    color: AppColors.onSurfaceVariant,
                  ),
                ),
              ],
            ),
          ),
          const Icon(CupertinoIcons.chevron_right,
              size: 14, color: AppColors.onSurfaceVariant),
        ],
      ),
    );
  }
}
