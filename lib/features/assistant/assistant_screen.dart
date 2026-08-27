import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_typography.dart';
import '../../core/theme/tokens.dart';
import '../../core/widgets/widgets.dart';

/// WeatherGPT Assistant Refined — AI chat interface
class AssistantScreen extends StatefulWidget {
  const AssistantScreen({super.key});

  @override
  State<AssistantScreen> createState() => _AssistantScreenState();
}

class _AssistantScreenState extends State<AssistantScreen> {
  final _controller = TextEditingController();
  final _messages = <_ChatMessage>[
    _ChatMessage(
      isUser: false,
      text: 'Good morning! I can see heavy rainfall is expected between '
          '8:20–8:45 AM along your usual route to Cyber Hub. '
          'Would you like me to analyze your commute options?',
      time: '7:55 AM',
    ),
    _ChatMessage(
      isUser: true,
      text: 'Yes, what\'s the safest way to get there by 9?',
      time: '7:56 AM',
    ),
    _ChatMessage(
      isUser: false,
      text: 'Based on current conditions, I recommend the Metro via Aqua Line. '
          'Risk score drops from 78 (Bike) to just 12. '
          'The ETA is 75 minutes, getting you there by 9:15 AM. '
          'Alternatively, delaying your bike departure to 9:30 AM reduces risk to 25.',
      time: '7:56 AM',
    ),
  ];

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.warmIvory,
      appBar: AppBar(
        leading: IconButton(
          icon: const Icon(CupertinoIcons.back),
          onPressed: () => context.pop(),
        ),
        title: Row(
          children: [
            Container(
              width: 32,
              height: 32,
              decoration: BoxDecoration(
                color: AppColors.sunriseAmber.withValues(alpha: 0.15),
                shape: BoxShape.circle,
              ),
              child: const Icon(CupertinoIcons.sparkles,
                  color: AppColors.sunriseAmber, size: 16),
            ),
            const SizedBox(width: 8),
            const Text('WeatherGPT'),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(CupertinoIcons.ellipsis_vertical),
            onPressed: () {},
          ),
        ],
      ),
      body: Column(
        children: [
          // ── Messages ──
          Expanded(
            child: ListView.builder(
              padding: const EdgeInsets.all(Spacing.pagePadding),
              itemCount: _messages.length,
              itemBuilder: (context, index) {
                final msg = _messages[index];
                return _buildMessage(msg);
              },
            ),
          ),

          // ── Input Bar ──
          Container(
            padding: EdgeInsets.only(
              left: Spacing.pagePadding,
              right: Spacing.pagePadding,
              top: 12,
              bottom: MediaQuery.of(context).padding.bottom + 12,
            ),
            decoration: const BoxDecoration(
              color: AppColors.warmIvory,
              border: Border(
                top: BorderSide(color: AppColors.cardBorderWarm, width: 1),
              ),
            ),
            child: Row(
              children: [
                Expanded(
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 16),
                    decoration: BoxDecoration(
                      color: AppColors.cardBackground,
                      borderRadius: BorderRadius.circular(Radii.full),
                      border: Border.all(color: AppColors.outlineVariant),
                    ),
                    child: TextField(
                      controller: _controller,
                      style: AppTypography.bodyMd.copyWith(
                        color: AppColors.primaryText,
                      ),
                      decoration: InputDecoration(
                        hintText: 'Ask about your commute...',
                        hintStyle: AppTypography.bodyMd.copyWith(
                          color: AppColors.outline,
                        ),
                        border: InputBorder.none,
                        contentPadding: const EdgeInsets.symmetric(vertical: 12),
                      ),
                      onSubmitted: _sendMessage,
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                GestureDetector(
                  onTap: () => context.push('/voice'),
                  child: Container(
                    width: 44,
                    height: 44,
                    decoration: const BoxDecoration(
                      color: AppColors.sunriseAmber,
                      shape: BoxShape.circle,
                    ),
                    child: const Icon(CupertinoIcons.mic_fill,
                        color: Colors.white, size: 20),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildMessage(_ChatMessage msg) {
    return Padding(
      padding: const EdgeInsets.only(bottom: Spacing.stackMd),
      child: Row(
        mainAxisAlignment:
            msg.isUser ? MainAxisAlignment.end : MainAxisAlignment.start,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (!msg.isUser) ...[
            Container(
              width: 32,
              height: 32,
              decoration: BoxDecoration(
                color: AppColors.sunriseAmber.withValues(alpha: 0.15),
                shape: BoxShape.circle,
              ),
              child: const Icon(CupertinoIcons.sparkles,
                  color: AppColors.sunriseAmber, size: 14),
            ),
            const SizedBox(width: 8),
          ],
          Flexible(
            child: Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: msg.isUser
                    ? AppColors.primaryContainer
                    : AppColors.cardBackground,
                borderRadius: BorderRadius.circular(Radii.card),
                boxShadow: msg.isUser
                    ? null
                    : const [
                        BoxShadow(
                          offset: Offset(0, 4),
                          blurRadius: 12,
                          color: AppColors.softShadow,
                        ),
                      ],
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    msg.text,
                    style: AppTypography.bodySm.copyWith(
                      color: msg.isUser
                          ? AppColors.onPrimary
                          : AppColors.primaryText,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    msg.time,
                    style: AppTypography.labelCaps.copyWith(
                      color: msg.isUser
                          ? AppColors.onPrimaryContainer
                          : AppColors.outline,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  void _sendMessage(String text) {
    if (text.trim().isEmpty) return;
    setState(() {
      _messages.add(_ChatMessage(isUser: true, text: text, time: '7:57 AM'));
      _controller.clear();
      // Simulate AI response
      Future.delayed(const Duration(milliseconds: 800), () {
        if (mounted) {
          setState(() {
            _messages.add(_ChatMessage(
              isUser: false,
              text: 'I\'ll analyze that for you. Based on current weather data '
                  'from IMD and live traffic conditions, here\'s what I recommend...',
              time: '7:57 AM',
            ));
          });
        }
      });
    });
  }
}

class _ChatMessage {
  final bool isUser;
  final String text;
  final String time;

  const _ChatMessage({
    required this.isUser,
    required this.text,
    required this.time,
  });
}
