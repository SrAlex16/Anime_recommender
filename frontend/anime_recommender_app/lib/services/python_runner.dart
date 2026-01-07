// lib/services/python_runner.dart
import 'api_service.dart'; // ✅ NUEVO IMPORT

// Esta clase ahora actúa como un "Runner" que usa la API externa.
// Su nombre se mantiene por compatibilidad con la lógica anterior.
class PythonRunner {
  static Future<Map<String, dynamic>> runTrainModel({required String username}) async {
    try {
      print('🚀 Conectando con API externa...');
      
      // ✅ LLAMAR A LA API EN LUGAR DE EJECUTAR PYTHON LOCAL
      final result = await ApiService.getRecommendations(username);
      
      // La API devuelve el objeto de datos completo
      if (result['status'] == 'success') {
        // 💡 CRÍTICO: Usar ?? [] y ?? {} para garantizar tipos no nulos.
        final recommendations = result['recommendations'] as List<dynamic>? ?? [];
        final statistics = result['statistics'] as Map<String, dynamic>? ?? {};

        print('🎯 ${recommendations.length} recomendaciones recibidas');
        print('📊 Estadísticas: ${statistics.isNotEmpty ? 'SÍ' : 'NO'}');
        
        return {
          'recommendations': recommendations,
          'statistics': statistics,
          'timestamp': result['timestamp'] as String? ?? '',
          'count': recommendations.length,
        };
      } else {
        // Manejar caso de status: 'error'
        throw Exception(result['message'] ?? 'Error desconocido de la API');
      }
      
    } catch (e) {
      print('❌ Error conectando con API: $e');
      throw Exception('No se pudo generar recomendaciones: $e');
    }
  }
}