// lib/services/python_runner.dart
import 'dart:convert';
import 'api_service.dart'; // ✅ NUEVO IMPORT

class PythonRunner {
  static Future<Map<String, dynamic>> runTrainModel({required String username}) async {
    try {
      print('🚀 Conectando con API externa...');
      
      // ✅ LLAMAR A LA API EN LUGAR DE EJECUTAR PYTHON LOCAL
      final result = await ApiService.getRecommendations(username);
      
      if (result['status'] == 'success') {
        print('🎯 ${result['recommendations']?.length ?? 0} recomendaciones recibidas');
        print('📊 Estadísticas: ${result['statistics'] != null ? 'SÍ' : 'NO'}');
        
        return {
          'recommendations': result['recommendations'] as List<dynamic>,
          'statistics': result['statistics'] as Map<String, dynamic>,
          'timestamp': result['timestamp'] as String,
          'count': result['count'] as int
        };
      } else {
        throw Exception(result['message'] ?? 'Error desconocido de la API');
      }
      
    } catch (e) {
      print('❌ Error conectando con API: $e');
      throw Exception('No se pudieron generar recomendaciones: $e');
    }
  }
}