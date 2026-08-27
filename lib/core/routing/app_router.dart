import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../features/home/home_screen.dart';
import '../../features/trip_analysis/trip_analysis_screen.dart';
import '../../features/alerts/alerts_feed_screen.dart';
import '../../features/profile/profile_screen.dart';
import '../../features/assistant/assistant_screen.dart';
import '../../features/what_if/what_if_screen.dart';
import '../../features/mode_comparison/mode_comparison_screen.dart';
import '../../features/risk_confidence/risk_confidence_screen.dart';
import '../../features/official_alert/official_alert_screen.dart';
import '../../features/local_hazard/local_hazard_screen.dart';
import '../../features/voice/voice_input_screen.dart';
import '../../features/historical_replay/historical_replay_screen.dart';
import '../theme/app_colors.dart';
import '../theme/app_typography.dart';

final _rootNavigatorKey = GlobalKey<NavigatorState>();

final appRouter = GoRouter(
  navigatorKey: _rootNavigatorKey,
  initialLocation: '/home',
  routes: [
    StatefulShellRoute.indexedStack(
      builder: (context, state, navigationShell) {
        return AppShell(navigationShell: navigationShell);
      },
      branches: [
        StatefulShellBranch(
          routes: [
            GoRoute(
              path: '/home',
              builder: (context, state) => const HomeScreen(),
            ),
          ],
        ),
        StatefulShellBranch(
          routes: [
            GoRoute(
              path: '/trips',
              builder: (context, state) => const TripAnalysisScreen(),
            ),
          ],
        ),
        StatefulShellBranch(
          routes: [
            GoRoute(
              path: '/alerts',
              builder: (context, state) => const AlertsFeedScreen(),
            ),
          ],
        ),
        StatefulShellBranch(
          routes: [
            GoRoute(
              path: '/profile',
              builder: (context, state) => const ProfileScreen(),
            ),
          ],
        ),
      ],
    ),
    // ── Full-screen routes outside the shell ──
    GoRoute(
      path: '/assistant',
      parentNavigatorKey: _rootNavigatorKey,
      builder: (context, state) => const AssistantScreen(),
    ),
    GoRoute(
      path: '/what-if',
      parentNavigatorKey: _rootNavigatorKey,
      builder: (context, state) => const WhatIfScreen(),
    ),
    GoRoute(
      path: '/mode-comparison',
      parentNavigatorKey: _rootNavigatorKey,
      builder: (context, state) => const ModeComparisonScreen(),
    ),
    GoRoute(
      path: '/risk',
      parentNavigatorKey: _rootNavigatorKey,
      builder: (context, state) => const RiskConfidenceScreen(),
    ),
    GoRoute(
      path: '/alert-detail',
      parentNavigatorKey: _rootNavigatorKey,
      builder: (context, state) => const OfficialAlertScreen(),
    ),
    GoRoute(
      path: '/hazard',
      parentNavigatorKey: _rootNavigatorKey,
      builder: (context, state) => const LocalHazardScreen(),
    ),
    GoRoute(
      path: '/voice',
      parentNavigatorKey: _rootNavigatorKey,
      builder: (context, state) => const VoiceInputScreen(),
    ),
    GoRoute(
      path: '/history',
      parentNavigatorKey: _rootNavigatorKey,
      builder: (context, state) => const HistoricalReplayScreen(),
    ),
  ],
);

/// Main app shell with bottom navigation
class AppShell extends StatelessWidget {
  final StatefulNavigationShell navigationShell;

  const AppShell({super.key, required this.navigationShell});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: navigationShell,
      bottomNavigationBar: Container(
        decoration: const BoxDecoration(
          border: Border(
            top: BorderSide(
              color: AppColors.tabBarBorder,
              width: 1,
            ),
          ),
        ),
        child: SafeArea(
          child: Padding(
            padding: const EdgeInsets.only(top: 8, bottom: 4),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceAround,
              children: [
                _NavItem(
                  icon: CupertinoIcons.cloud_sun,
                  label: 'Home',
                  isActive: navigationShell.currentIndex == 0,
                  onTap: () => navigationShell.goBranch(0),
                ),
                _NavItem(
                  icon: CupertinoIcons.map,
                  label: 'Trips',
                  isActive: navigationShell.currentIndex == 1,
                  onTap: () => navigationShell.goBranch(1),
                ),
                _NavItem(
                  icon: CupertinoIcons.bell,
                  label: 'Alerts',
                  isActive: navigationShell.currentIndex == 2,
                  onTap: () => navigationShell.goBranch(2),
                ),
                _NavItem(
                  icon: CupertinoIcons.person,
                  label: 'Profile',
                  isActive: navigationShell.currentIndex == 3,
                  onTap: () => navigationShell.goBranch(3),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _NavItem extends StatelessWidget {
  final IconData icon;
  final String label;
  final bool isActive;
  final VoidCallback onTap;

  const _NavItem({
    required this.icon,
    required this.label,
    required this.isActive,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      behavior: HitTestBehavior.opaque,
      child: SizedBox(
        width: 64,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              icon,
              size: 24,
              color: isActive ? AppColors.tabActive : AppColors.tabInactive,
            ),
            const SizedBox(height: 4),
            Text(
              label,
              style: AppTypography.labelCaps.copyWith(
                color: isActive ? AppColors.tabActive : AppColors.tabInactive,
                fontSize: 10,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
