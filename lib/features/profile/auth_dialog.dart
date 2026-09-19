import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_typography.dart';
import '../../core/theme/tokens.dart';
import '../../core/providers.dart';

/// Modal dialog for traveler authentication: email sign-in, account creation, or quick demo login.
class AuthDialog extends ConsumerStatefulWidget {
  final String? title;
  final String? subtitle;

  const AuthDialog({
    super.key,
    this.title,
    this.subtitle,
  });

  static Future<void> show(
    BuildContext context, {
    String? title,
    String? subtitle,
  }) {
    return showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) => AuthDialog(title: title, subtitle: subtitle),
    );
  }

  @override
  ConsumerState<AuthDialog> createState() => _AuthDialogState();
}

class _AuthDialogState extends ConsumerState<AuthDialog> {
  final _emailController = TextEditingController(text: 'traveler@weathergpt.com');
  final _passwordController = TextEditingController(text: 'password123');
  bool _isSignUp = false;
  bool _isLoading = false;
  String? _errorMessage;

  @override
  void dispose() {
    _emailController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final email = _emailController.text.trim();
    final password = _passwordController.text.trim();

    if (email.isEmpty || password.isEmpty) {
      setState(() => _errorMessage = 'Please enter both email and password.');
      return;
    }

    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      if (_isSignUp) {
        await ref.read(authStateProvider.notifier).createUserWithEmail(email, password);
      } else {
        await ref.read(authStateProvider.notifier).signInWithEmail(email, password);
      }
      if (mounted) {
        Navigator.of(context).pop();
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _isLoading = false;
          _errorMessage = e.toString().replaceAll('Exception: ', '');
        });
      }
    }
  }

  Future<void> _quickDemoLogin() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      await ref.read(authStateProvider.notifier).signInWithMockUser(
            uid: 'demo-user-om',
            email: 'om@weathergpt.com',
            displayName: 'Om Gangwar',
          );
      if (mounted) {
        Navigator.of(context).pop();
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _isLoading = false;
          _errorMessage = e.toString();
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final bottomInset = MediaQuery.of(context).viewInsets.bottom;

    return Container(
      decoration: const BoxDecoration(
        color: AppColors.cardBackground,
        borderRadius: BorderRadius.vertical(top: Radius.circular(Radii.card)),
      ),
      padding: EdgeInsets.only(
        left: Spacing.pagePadding,
        right: Spacing.pagePadding,
        top: 24,
        bottom: bottomInset > 0 ? bottomInset + 16 : 32,
      ),
      child: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // ── Drag Handle & Header ──
            Center(
              child: Container(
                width: 40,
                height: 4,
                decoration: BoxDecoration(
                  color: AppColors.outlineVariant,
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
            ),
            const SizedBox(height: Spacing.stackMd),

            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Expanded(
                  child: Text(
                    widget.title ?? (_isSignUp ? 'Create Account' : 'Welcome to WeatherGPT'),
                    style: AppTypography.headlineMd.copyWith(
                      color: AppColors.primaryText,
                    ),
                  ),
                ),
                IconButton(
                  icon: const Icon(CupertinoIcons.xmark_circle_fill, color: AppColors.outline),
                  onPressed: () => Navigator.of(context).pop(),
                  tooltip: 'Close',
                ),
              ],
            ),
            if (widget.subtitle != null) ...[
              const SizedBox(height: 4),
              Text(
                widget.subtitle!,
                style: AppTypography.bodySm.copyWith(
                  color: AppColors.onSurfaceVariant,
                ),
              ),
            ],
            const SizedBox(height: Spacing.stackMd),

            // ── Error Message Banner ──
            if (_errorMessage != null) ...[
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: AppColors.riskSevereBg,
                  borderRadius: BorderRadius.circular(Radii.base),
                  border: Border.all(color: AppColors.riskSevere.withValues(alpha: 0.3)),
                ),
                child: Row(
                  children: [
                    const Icon(CupertinoIcons.exclamationmark_triangle, color: AppColors.riskSevere, size: 18),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        _errorMessage!,
                        style: AppTypography.bodySm.copyWith(color: AppColors.riskSevere),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: Spacing.stackMd),
            ],

            // ── Inputs ──
            Text(
              'EMAIL',
              style: AppTypography.labelCaps.copyWith(color: AppColors.outline),
            ),
            const SizedBox(height: 6),
            TextField(
              controller: _emailController,
              keyboardType: TextInputType.emailAddress,
              style: AppTypography.bodyMd.copyWith(color: AppColors.primaryText),
              decoration: InputDecoration(
                hintText: 'Enter your email',
                hintStyle: AppTypography.bodyMd.copyWith(color: AppColors.outline),
                prefixIcon: const Icon(CupertinoIcons.mail, size: 18, color: AppColors.outline),
                filled: true,
                fillColor: AppColors.surfaceContainerLow,
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(Radii.base),
                  borderSide: const BorderSide(color: AppColors.cardBorderWarm),
                ),
                enabledBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(Radii.base),
                  borderSide: const BorderSide(color: AppColors.cardBorderWarm),
                ),
                contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
              ),
            ),
            const SizedBox(height: Spacing.stackMd),

            Text(
              'PASSWORD',
              style: AppTypography.labelCaps.copyWith(color: AppColors.outline),
            ),
            const SizedBox(height: 6),
            TextField(
              controller: _passwordController,
              obscureText: true,
              style: AppTypography.bodyMd.copyWith(color: AppColors.primaryText),
              decoration: InputDecoration(
                hintText: 'Enter your password',
                hintStyle: AppTypography.bodyMd.copyWith(color: AppColors.outline),
                prefixIcon: const Icon(CupertinoIcons.lock, size: 18, color: AppColors.outline),
                filled: true,
                fillColor: AppColors.surfaceContainerLow,
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(Radii.base),
                  borderSide: const BorderSide(color: AppColors.cardBorderWarm),
                ),
                enabledBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(Radii.base),
                  borderSide: const BorderSide(color: AppColors.cardBorderWarm),
                ),
                contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
              ),
            ),
            const SizedBox(height: Spacing.stackLg),

            // ── Primary Action Button ──
            ElevatedButton(
              onPressed: _isLoading ? null : _submit,
              style: ElevatedButton.styleFrom(
                backgroundColor: AppColors.sunriseAmber,
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(vertical: 14),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(Radii.base)),
                elevation: 0,
              ),
              child: _isLoading
                  ? const SizedBox(
                      width: 20,
                      height: 20,
                      child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2),
                    )
                  : Text(
                      _isSignUp ? 'Create Account' : 'Sign In',
                      style: AppTypography.labelMd.copyWith(
                        color: Colors.white,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
            ),
            const SizedBox(height: Spacing.stackSm),

            // ── Demo / Quick Sign-in Button ──
            OutlinedButton(
              onPressed: _isLoading ? null : _quickDemoLogin,
              style: OutlinedButton.styleFrom(
                side: const BorderSide(color: AppColors.sunriseAmber),
                padding: const EdgeInsets.symmetric(vertical: 14),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(Radii.base)),
              ),
              child: Text(
                'Quick Demo Sign-In',
                style: AppTypography.labelMd.copyWith(
                  color: AppColors.sunriseAmber,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
            const SizedBox(height: Spacing.stackSm),

            // ── Toggle Switch ──
            TextButton(
              onPressed: () {
                setState(() {
                  _isSignUp = !_isSignUp;
                  _errorMessage = null;
                });
              },
              child: Text(
                _isSignUp ? 'Already have an account? Sign In' : "Don't have an account? Create one",
                style: AppTypography.bodySm.copyWith(
                  color: AppColors.primaryText,
                  decoration: TextDecoration.underline,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
