enum ApiErrorType {
  networkError,
  timeout,
  serverError,
  validationError,
  routingUnavailable,
  weatherUnavailable,
  dataUnavailable,
  unauthorized,
  forbidden,
  rateLimited,
  unknown,
}

class ApiException implements Exception {
  final ApiErrorType type;
  final String message;
  final int? statusCode;
  final int? retryAfter;

  ApiException({
    required this.type,
    required this.message,
    this.statusCode,
    this.retryAfter,
  });

  @override
  String toString() {
    if (retryAfter != null) {
      return 'ApiException(type: $type, statusCode: $statusCode, retryAfter: $retryAfter, message: $message)';
    }
    return 'ApiException(type: $type, statusCode: $statusCode, message: $message)';
  }
}

