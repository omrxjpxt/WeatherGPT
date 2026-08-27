enum ApiErrorType {
  networkError,
  timeout,
  serverError,
  validationError,
  routingUnavailable,
  weatherUnavailable,
  dataUnavailable,
  unknown,
}

class ApiException implements Exception {
  final ApiErrorType type;
  final String message;
  final int? statusCode;

  ApiException({
    required this.type,
    required this.message,
    this.statusCode,
  });

  @override
  String toString() {
    return 'ApiException(type: $type, statusCode: $statusCode, message: $message)';
  }
}
