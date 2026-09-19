import 'package:flutter_test/flutter_test.dart';
import 'package:weather_gpt/models/models.dart';

void main() {
  group('User Persistence Models Serialization & Deserialization Tests', () {
    test('UserProfile round-trip serialization and camelCase contract', () {
      final now = DateTime.utc(2026, 9, 19, 1, 0, 0);
      final json = {
        'uid': 'user-123',
        'email': 'om@weathergpt.com',
        'displayName': 'Om Gangwar',
        'createdAt': now.toIso8601String(),
        'lastLoginAt': now.toIso8601String(),
      };

      final profile = UserProfile.fromJson(json);

      expect(profile.uid, 'user-123');
      expect(profile.email, 'om@weathergpt.com');
      expect(profile.displayName, 'Om Gangwar');

      final serialized = profile.toJson();
      expect(serialized['uid'], 'user-123');
      expect(serialized['email'], 'om@weathergpt.com');
      expect(serialized['displayName'], 'Om Gangwar');
      expect(serialized['createdAt'], now.toIso8601String());
      expect(serialized['lastLoginAt'], now.toIso8601String());
    });

    test('UserProfile handles null email and displayName gracefully', () {
      final json = {
        'uid': 'guest-anonymous-456',
      };

      final profile = UserProfile.fromJson(json);

      expect(profile.uid, 'guest-anonymous-456');
      expect(profile.email, isNull);
      expect(profile.displayName, isNull);
      expect(profile.createdAt, isNotNull);
      expect(profile.lastLoginAt, isNotNull);

      final serialized = profile.toJson();
      expect(serialized['uid'], 'guest-anonymous-456');
      expect(serialized.containsKey('email'), isFalse);
      expect(serialized.containsKey('displayName'), isFalse);
    });

    test('SavedRoute round-trip serialization and camelCase keys', () {
      final now = DateTime.utc(2026, 9, 19, 2, 30, 0);
      final json = {
        'id': 'route-cyberhub',
        'name': 'Home to Cyber Hub',
        'originId': 'Noida Sector 62',
        'destinationId': 'Gurgaon Cyber Hub',
        'createdAt': now.toIso8601String(),
      };

      final saved = SavedRoute.fromJson(json);

      expect(saved.id, 'route-cyberhub');
      expect(saved.name, 'Home to Cyber Hub');
      expect(saved.originId, 'Noida Sector 62');
      expect(saved.destinationId, 'Gurgaon Cyber Hub');

      final serialized = saved.toJson();
      expect(serialized['id'], 'route-cyberhub');
      expect(serialized['name'], 'Home to Cyber Hub');
      expect(serialized['originId'], 'Noida Sector 62');
      expect(serialized['destinationId'], 'Gurgaon Cyber Hub');
      expect(serialized['createdAt'], now.toIso8601String());
    });

    test('TripHistorySummary round-trip serialization and snapshot default', () {
      final now = DateTime.utc(2026, 9, 18, 18, 45, 0);
      final json = {
        'analysisId': 'analysis-uuid-789',
        'status': 'success',
        'origin': 'Noida Sector 62',
        'destination': 'Gurgaon Cyber Hub',
        'mode': 'bike',
        'riskLevel': 'low',
        'recommendationHeadline': 'Clear route via expressway',
        'createdAt': now.toIso8601String(),
        'isSnapshot': true,
      };

      final summary = TripHistorySummary.fromJson(json);

      expect(summary.analysisId, 'analysis-uuid-789');
      expect(summary.status, 'success');
      expect(summary.origin, 'Noida Sector 62');
      expect(summary.destination, 'Gurgaon Cyber Hub');
      expect(summary.mode, 'bike');
      expect(summary.riskLevel, 'low');
      expect(summary.recommendationHeadline, 'Clear route via expressway');
      expect(summary.isSnapshot, isTrue);

      final serialized = summary.toJson();
      expect(serialized['analysisId'], 'analysis-uuid-789');
      expect(serialized['riskLevel'], 'low');
      expect(serialized['recommendationHeadline'], 'Clear route via expressway');
      expect(serialized['isSnapshot'], isTrue);
    });

    test('ConversationSummary serialization with camelCase tripId', () {
      final now = DateTime.utc(2026, 9, 19, 0, 15, 0);
      final json = {
        'id': 'conv-101',
        'tripId': 'trip-analysis-101',
        'title': 'Commute to Gurgaon',
        'createdAt': now.toIso8601String(),
      };

      final conv = ConversationSummary.fromJson(json);

      expect(conv.id, 'conv-101');
      expect(conv.tripId, 'trip-analysis-101');
      expect(conv.title, 'Commute to Gurgaon');

      final serialized = conv.toJson();
      expect(serialized['id'], 'conv-101');
      expect(serialized['tripId'], 'trip-analysis-101');
      expect(serialized['title'], 'Commute to Gurgaon');
    });

    test('AssistantChatRequest backward compatibility with and without conversationId', () {
      // Without conversationId (older clients)
      final jsonWithoutConv = {
        'message': 'Can I travel by bike?',
        'contextOrigin': 'Noida',
        'contextDestination': 'Delhi',
      };

      final req1 = AssistantChatRequest.fromJson(jsonWithoutConv);
      expect(req1.message, 'Can I travel by bike?');
      expect(req1.conversationId, isNull);

      final serialized1 = req1.toJson();
      expect(serialized1.containsKey('conversationId'), isFalse);

      // With conversationId
      final jsonWithConv = {
        'message': 'What about traffic?',
        'conversationId': 'conv-xyz-555',
      };

      final req2 = AssistantChatRequest.fromJson(jsonWithConv);
      expect(req2.message, 'What about traffic?');
      expect(req2.conversationId, 'conv-xyz-555');

      final serialized2 = req2.toJson();
      expect(serialized2['conversationId'], 'conv-xyz-555');
    });
  });
}
