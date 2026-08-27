import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;
import 'api_config.dart';
import 'api_exception.dart';

class ApiClient {
  final http.Client _client = http.Client();

  Future<dynamic> get(String path, {Map<String, String>? queryParams}) async {
    final uri = Uri.parse('${ApiConfig.baseUrl}$path').replace(queryParameters: queryParams);
    return _performRequest(() => _client.get(uri, headers: _headers));
  }

  Future<dynamic> post(String path, {Map<String, dynamic>? body}) async {
    final uri = Uri.parse('${ApiConfig.baseUrl}$path');
    return _performRequest(() => _client.post(uri, headers: _headers, body: jsonEncode(body)));
  }

  Map<String, String> get _headers => {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      };

  Future<dynamic> _performRequest(Future<http.Response> Function() requestFunc) async {
    try {
      final response = await requestFunc().timeout(ApiConfig.timeout);
      return _handleResponse(response);
    } on TimeoutException {
      throw ApiException(
        type: ApiErrorType.timeout,
        message: 'The connection has timed out, please try again.',
      );
    } on SocketException catch (e) {
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

      if (response.statusCode == 422) {
        errorType = ApiErrorType.validationError;
        message = 'Invalid request parameters.';
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

      throw ApiException(
        type: errorType,
        message: message,
        statusCode: response.statusCode,
      );
    }
  }
}
