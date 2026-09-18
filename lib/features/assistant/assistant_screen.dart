import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_typography.dart';
import '../../core/theme/tokens.dart';
import '../../core/providers.dart';
import '../../models/models.dart';

/// WeatherGPT Assistant Refined — AI chat interface connected to FastAPI backend
class AssistantScreen extends ConsumerStatefulWidget {
  const AssistantScreen({super.key});

  @override
  ConsumerState<AssistantScreen> createState() => _AssistantScreenState();
}

class _AssistantScreenState extends ConsumerState<AssistantScreen> {
  final _controller = TextEditingController();
  final _scrollController = ScrollController();
  bool _isLoading = false;

  final _messages = <_ChatMessage>[
    const _ChatMessage(
      isUser: false,
      text: 'Good morning! I can help you plan weather-safe travel across Delhi-NCR. '
          'Where would you like to travel, and when?',
      time: 'Just now',
    ),
  ];

  @override
  void dispose() {
    _controller.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.warmIvory,
      appBar: AppBar(
        titleSpacing: 0,
        leading: IconButton(
          icon: const Icon(CupertinoIcons.back),
          onPressed: () => context.pop(),
        ),
        title: Row(
          mainAxisSize: MainAxisSize.min,
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
              controller: _scrollController,
              padding: const EdgeInsets.all(Spacing.pagePadding),
              itemCount: _messages.length + (_isLoading ? 1 : 0),
              itemBuilder: (context, index) {
                if (index == _messages.length && _isLoading) {
                  return _buildLoadingBubble();
                }
                final msg = _messages[index];
                return _buildMessage(msg);
              },
            ),
          ),

          // ── Input Bar ──
          Builder(
            builder: (context) {
              final isKeyboardOpen = MediaQuery.of(context).viewInsets.bottom > 0;
              final bottomPadding = isKeyboardOpen ? 12.0 : MediaQuery.of(context).padding.bottom + 12;
              return Container(
                padding: EdgeInsets.only(
                  left: Spacing.pagePadding,
                  right: Spacing.pagePadding,
                  top: 12,
                  bottom: bottomPadding,
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
              );
            },
          ),
        ],
      ),
    );
  }

  Widget _buildLoadingBubble() {
    return Padding(
      padding: const EdgeInsets.only(bottom: Spacing.stackMd),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
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
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            decoration: BoxDecoration(
              color: AppColors.cardBackground,
              borderRadius: BorderRadius.circular(Radii.card),
              boxShadow: const [
                BoxShadow(
                  offset: Offset(0, 4),
                  blurRadius: 12,
                  color: AppColors.softShadow,
                ),
              ],
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                const SizedBox(
                  width: 14,
                  height: 14,
                  child: CircularProgressIndicator(
                    strokeWidth: 2,
                    color: AppColors.sunriseAmber,
                  ),
                ),
                const SizedBox(width: 8),
                Text(
                  'Evaluating commute...',
                  style: AppTypography.bodySm.copyWith(
                    color: AppColors.onSurfaceVariant,
                    fontStyle: FontStyle.italic,
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
                  if (msg.tripRequest != null && msg.tripResponse != null) ...[
                    const SizedBox(height: 10),
                    GestureDetector(
                      onTap: () {
                        ref.read(activeTripRequestProvider.notifier).update(msg.tripRequest!);
                        context.push('/trips');
                      },
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                        decoration: BoxDecoration(
                          color: AppColors.sunriseAmber.withValues(alpha: 0.12),
                          borderRadius: BorderRadius.circular(Radii.full),
                          border: Border.all(
                            color: AppColors.sunriseAmber.withValues(alpha: 0.3),
                          ),
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            const Icon(CupertinoIcons.map, size: 14, color: AppColors.sunriseAmber),
                            const SizedBox(width: 6),
                            Flexible(
                              child: Text(
                                'View Trip Analysis',
                                style: AppTypography.labelMd.copyWith(
                                  color: AppColors.primaryText,
                                  fontWeight: FontWeight.w600,
                                ),
                                overflow: TextOverflow.ellipsis,
                              ),
                            ),
                            const SizedBox(width: 4),
                            const Icon(CupertinoIcons.chevron_right, size: 12, color: AppColors.outline),
                          ],
                        ),
                      ),
                    ),
                  ],
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

  void _sendMessage(String text) async {
    final query = text.trim();
    if (query.isEmpty) return;

    final now = DateTime.now();
    final timeStr = '${now.hour.toString().padLeft(2, '0')}:${now.minute.toString().padLeft(2, '0')}';

    setState(() {
      _messages.add(_ChatMessage(isUser: true, text: query, time: timeStr));
      _controller.clear();
      _isLoading = true;
    });
    _scrollToBottom();

    try {
      final repo = ref.read(assistantRepositoryProvider);
      final response = await repo.chat(AssistantChatRequest(message: query));

      if (mounted) {
        setState(() {
          _isLoading = false;
          _messages.add(_ChatMessage(
            isUser: false,
            text: response.message,
            time: timeStr,
            tripRequest: response.tripRequest,
            tripResponse: response.tripResponse,
            status: response.status,
          ));
        });
        _scrollToBottom();
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _isLoading = false;
          _messages.add(_ChatMessage(
            isUser: false,
            text: 'I could not reach the travel analysis service right now. Please try again in a moment.',
            time: timeStr,
            status: 'error',
          ));
        });
        _scrollToBottom();
      }
    }
  }
}

class _ChatMessage {
  final bool isUser;
  final String text;
  final String time;
  final TripRequest? tripRequest;
  final TripResponse? tripResponse;
  final String? status;

  const _ChatMessage({
    required this.isUser,
    required this.text,
    required this.time,
    this.tripRequest,
    this.tripResponse,
    this.status,
  });
}
