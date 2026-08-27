import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_typography.dart';
import '../../core/theme/tokens.dart';
import '../../core/widgets/widgets.dart';

/// Profile / Settings screen
class ProfileScreen extends StatelessWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context) {
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

              // ── User Card ──
              WeatherCard(
                child: Row(
                  children: [
                    Container(
                      width: 56,
                      height: 56,
                      decoration: BoxDecoration(
                        color: AppColors.sunriseAmber.withValues(alpha: 0.15),
                        shape: BoxShape.circle,
                      ),
                      child: const Icon(CupertinoIcons.person_fill,
                          color: AppColors.sunriseAmber, size: 28),
                    ),
                    const SizedBox(width: 16),
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Om Gangwar',
                          style: AppTypography.headlineMd.copyWith(
                            color: AppColors.primaryText,
                          ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          'Noida, Sector 62',
                          style: AppTypography.bodySm.copyWith(
                            color: AppColors.onSurfaceVariant,
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              const SizedBox(height: Spacing.stackLg),

              // ── Saved Routes ──
              const SectionTitle(title: 'Saved Routes'),
              const SizedBox(height: Spacing.stackMd),
              _SettingsCard(
                icon: CupertinoIcons.location,
                title: 'Home → Office',
                subtitle: 'Noida Sec 62 → Cyber Hub',
              ),
              const SizedBox(height: Spacing.stackSm),
              _SettingsCard(
                icon: CupertinoIcons.location,
                title: 'Home → DTU',
                subtitle: 'Noida Sec 62 → Delhi Tech University',
              ),
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

              // ── Data ──
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
