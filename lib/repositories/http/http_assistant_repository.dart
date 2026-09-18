import '../../models/models.dart';
import '../repositories.dart';
import '../../core/api/api_client.dart';

class HttpAssistantRepository implements AssistantRepository {
  final ApiClient _apiClient;

  HttpAssistantRepository(this._apiClient);

  @override
  Future<AssistantChatResponse> chat(AssistantChatRequest request) async {
    final response = await _apiClient.post('/assistant/chat', body: request.toJson());
    return AssistantChatResponse.fromJson(response as Map<String, dynamic>);
  }

  @override
  Future<AssistantParseResponse> parseIntent(String query, {DateTime? referenceTime}) async {
    final body = {
      'query': query,
      if (referenceTime != null) 'referenceTime': referenceTime.toUtc().toIso8601String(),
    };
    final response = await _apiClient.post('/assistant/parse', body: body);
    return AssistantParseResponse.fromJson(response as Map<String, dynamic>);
  }
}
