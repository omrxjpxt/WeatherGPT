import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_typography.dart';
import '../../core/theme/tokens.dart';
import '../../core/widgets/widgets.dart';
import '../../core/providers.dart';

/// Voice Input Refined — Listening state with transcript and extracted fields
class VoiceInputScreen extends ConsumerStatefulWidget {
  const VoiceInputScreen({super.key});

  @override
  ConsumerState<VoiceInputScreen> createState() => _VoiceInputScreenState();
}

class _VoiceInputScreenState extends ConsumerState<VoiceInputScreen>
    with SingleTickerProviderStateMixin {
  late AnimationController _pulseController;
  bool _hasStarted = false;

  @override
  void initState() {
    super.initState();
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1500),
    )..repeat(reverse: true);

    // Auto-start listening simulation
    Future.delayed(const Duration(milliseconds: 500), () {
      if (mounted) {
        ref.read(voiceSessionProvider.notifier).startListening();
        setState(() => _hasStarted = true);

        // Simulate transcript after 3 seconds
        Future.delayed(const Duration(seconds: 3), () {
          if (mounted) {
            ref.read(voiceSessionProvider.notifier).simulateTranscript(
              'Bhai kal subah 8 baje college jaana hai, bike se.',
            );
          }
        });
      }
    });
  }

  @override
  void dispose() {
    _pulseController.dispose();
    ref.read(voiceSessionProvider.notifier).reset();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final session = ref.watch(voiceSessionProvider);

    return Scaffold(
      backgroundColor: AppColors.warmIvory,
      appBar: AppBar(
        leading: IconButton(
          icon: const Icon(CupertinoIcons.xmark),
          onPressed: () => context.pop(),
        ),
        title: const Text('Voice Input'),
      ),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: Spacing.pagePadding),
          child: Column(
            children: [
              const Spacer(),

              // ── Mic Button with Pulse ──
              AnimatedBuilder(
                animation: _pulseController,
                builder: (context, child) {
                  final scale = session.isListening
                      ? 1.0 + (_pulseController.value * 0.15)
                      : 1.0;
                  return Transform.scale(
                    scale: scale,
                    child: Container(
                      width: 120,
                      height: 120,
                      decoration: BoxDecoration(
                        color: session.isListening
                            ? AppColors.sunriseAmber
                            : AppColors.surfaceContainerHigh,
                        shape: BoxShape.circle,
                        boxShadow: session.isListening
                            ? [
                                BoxShadow(
                                  color: AppColors.sunriseAmber.withValues(alpha: 0.3),
                                  blurRadius: 40,
                                  spreadRadius: 10,
                                ),
                              ]
                            : null,
                      ),
                      child: Icon(
                        session.isListening
                            ? CupertinoIcons.mic_fill
                            : CupertinoIcons.mic,
                        color: session.isListening
                            ? Colors.white
                            : AppColors.onSurfaceVariant,
                        size: 48,
                      ),
                    ),
                  );
                },
              ),
              const SizedBox(height: Spacing.stackLg),

              // ── Status Text ──
              Text(
                session.isListening
                    ? 'Listening...'
                    : session.transcript.isNotEmpty
                        ? 'Got it!'
                        : 'Tap to speak',
                style: AppTypography.headlineLgMobile.copyWith(
                  color: AppColors.primaryText,
                ),
              ),
              const SizedBox(height: Spacing.stackSm),
              Text(
                session.isListening
                    ? 'Speak naturally in any language'
                    : session.transcript.isNotEmpty
                        ? 'Here\'s what I understood'
                        : 'Tell me about your trip',
                style: AppTypography.bodySm.copyWith(
                  color: AppColors.onSurfaceVariant,
                ),
              ),

              const Spacer(),

              // ── Transcript ──
              if (session.transcript.isNotEmpty) ...[
                WeatherCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const SectionTitle(title: 'Transcript'),
                      const SizedBox(height: Spacing.stackSm),
                      Text(
                        '"${session.transcript}"',
                        style: AppTypography.bodyMd.copyWith(
                          color: AppColors.primaryText,
                          fontStyle: FontStyle.italic,
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: Spacing.stackMd),
              ],

              // ── Extracted Trip Fields ──
              if (session.extractedTrip != null) ...[
                WeatherCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const SectionTitle(title: 'Extracted Trip'),
                      const SizedBox(height: Spacing.stackMd),
                      _ExtractedField(
                        icon: CupertinoIcons.location,
                        label: 'Destination',
                        value: session.extractedTrip!.destination,
                      ),
                      const SizedBox(height: Spacing.stackSm),
                      _ExtractedField(
                        icon: CupertinoIcons.calendar,
                        label: 'When',
                        value: 'Tomorrow',
                      ),
                      const SizedBox(height: Spacing.stackSm),
                      _ExtractedField(
                        icon: CupertinoIcons.clock,
                        label: 'Time',
                        value: '8:00 AM',
                      ),
                      const SizedBox(height: Spacing.stackSm),
                      _ExtractedField(
                        icon: Icons.two_wheeler,
                        label: 'Mode',
                        value: 'Two-wheeler',
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: Spacing.stackMd),

                // ── Analyze Button ──
                GestureDetector(
                  onTap: () => context.go('/trips'),
                  child: Container(
                    width: double.infinity,
                    padding: const EdgeInsets.symmetric(vertical: 16),
                    decoration: BoxDecoration(
                      color: AppColors.primaryContainer,
                      borderRadius: BorderRadius.circular(Radii.full),
                    ),
                    child: Center(
                      child: Text(
                        'Analyze Trip',
                        style: AppTypography.buttonLabel.copyWith(
                          color: AppColors.onPrimary,
                        ),
                      ),
                    ),
                  ),
                ),
              ],

              const SizedBox(height: Spacing.stackLg),
            ],
          ),
        ),
      ),
    );
  }
}

class _ExtractedField extends StatelessWidget {
  final IconData icon;
  final String label;
  final String value;

  const _ExtractedField({
    required this.icon,
    required this.label,
    required this.value,
  });

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Icon(icon, size: 18, color: AppColors.sunriseAmber),
        const SizedBox(width: 12),
        Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(label,
                style: AppTypography.labelCaps.copyWith(
                    color: AppColors.onSurfaceVariant)),
            Text(value,
                style: AppTypography.labelMd.copyWith(
                    color: AppColors.primaryText, fontWeight: FontWeight.w600)),
          ],
        ),
      ],
    );
  }
}
