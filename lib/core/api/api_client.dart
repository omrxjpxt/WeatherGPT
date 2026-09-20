import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;
import 'api_config.dart';
import 'api_exception.dart';

class ApiClient {
  final http.Client _client;
  final Future<String?> Function()? tokenProvider;

  ApiClient({
    http.Client? client,
    this.tokenProvider,
  }) : _client = client ?? http.Client();

  Future<dynamic> get(String path, {Map<String, String>? queryParams}) async {
    final uri = Uri.parse('${ApiConfig.baseUrl}$path').replace(queryParameters: queryParams);
    final headers = await _buildHeaders();
    return _performRequest(() => _client.get(uri, headers: headers));
  }

  Future<dynamic> post(String path, {Map<String, dynamic>? body}) async {
    final uri = Uri.parse('${ApiConfig.baseUrl}$path');
    final headers = await _buildHeaders();
    return _performRequest(() => _client.post(uri, headers: headers, body: jsonEncode(body)));
  }

  Future<dynamic> put(String path, {Map<String, dynamic>? body}) async {
    final uri = Uri.parse('${ApiConfig.baseUrl}$path');
    final headers = await _buildHeaders();
    return _performRequest(() => _client.put(uri, headers: headers, body: jsonEncode(body)));
  }

  Future<dynamic> delete(String path) async {
    final uri = Uri.parse('${ApiConfig.baseUrl}$path');
    final headers = await _buildHeaders();
    return _performRequest(() => _client.delete(uri, headers: headers));
  }

  Future<Map<String, String>> _buildHeaders() async {
    final headers = <String, String>{
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    };

    if (tokenProvider != null) {
      try {
        final token = await tokenProvider!();
        if (token != null && token.isNotEmpty) {
          headers['Authorization'] = 'Bearer $token';
        }
      } catch (_) {
        // Token retrieval failure does not crash the request; request proceeds as unauthenticated
      }
    }

    return headers;
  }

  Future<dynamic> _performRequest(Future<http.Response> Function() requestFunc) async {
    try {
      final response = await requestFunc().timeout(ApiConfig.timeout);
      return _handleResponse(response);
    } on TimeoutException {
      throw ApiException(
        type: ApiErrorType.timeout,
        message: 'The connection has timed out, please try again.',
      );
    } on SocketException {
      throw ApiException(
        type: ApiErrorType.networkError,
        message: 'No internet connection or backend unreachable.',
      );
    } catch (e) {
      if (e is ApiException) rethrow;
      throw ApiException(
        type: ApiErrorType.unknown,
        message: 'An unexpected error occurred: $e',
      );
    }
  }

  dynamic _handleResponse(http.Response response) {
    if (response.statusCode >= 200 && response.statusCode < 300) {
      if (response.body.isEmpty) return null;
      try {
        return jsonDecode(response.body);
      } catch (e) {
        throw ApiException(
          type: ApiErrorType.dataUnavailable,
          message: 'Malformed JSON response from server.',
          statusCode: response.statusCode,
        );
      }
    } else {
      ApiErrorType errorType = ApiErrorType.serverError;
      String message = 'Server error occurred.';

      int? retryAfter;

      if (response.statusCode == 401) {
        errorType = ApiErrorType.unauthorized;
        message = 'Authentication required or session expired.';
      } else if (response.statusCode == 403) {
        errorType = ApiErrorType.forbidden;
        message = 'Access forbidden.';
      } else if (response.statusCode == 422) {
        errorType = ApiErrorType.validationError;
        message = 'Invalid request parameters.';
      } else if (response.statusCode == 429) {
        errorType = ApiErrorType.rateLimited;
        final retryHeader = response.headers['retry-after'];
        if (retryHeader != null) {
          retryAfter = int.tryParse(retryHeader);
        }
        message = retryAfter != null
            ? 'Rate limit exceeded. Please try again in $retryAfter seconds.'
            : 'Rate limit exceeded. Please wait a moment before trying again.';
      } else if (response.statusCode == 503) {
        errorType = ApiErrorType.routingUnavailable;
        message = 'Service temporarily unavailable.';
      }

      // Try to parse detail from FastAPI
      try {
        final decoded = jsonDecode(response.body);
        if (decoded is Map<String, dynamic> && decoded.containsKey('detail')) {
          final detail = decoded['detail'];
          if (detail is String) {
            message = detail;
          } else if (detail is List) {
            message = detail.map((e) => e['msg']).join(', ');
          }
        }
      } catch (_) {}

      if (response.statusCode == 429 && retryAfter != null && !message.contains('$retryAfter')) {
        message = '$message Please try again in $retryAfter seconds.';
      }

      throw ApiException(
        type: errorType,
        message: message,
        statusCode: response.statusCode,
        retryAfter: retryAfter,
      );
    }
  }
}
