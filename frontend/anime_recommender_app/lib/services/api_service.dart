// lib/services/api_service.dart
import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart'; // Importar para persistencia

class ApiService {
  // URL del endpoint de Render
  static const String baseUrl = 'https://anime-recommender-1-x854.onrender.com'; 
  
  // Clave base para SharedPreferences, usando el nombre de usuario para diferenciar
  static const String _storageKeyBase = 'recommendations_data_';

  // --- MÉTODOS DE LA API ---
  // ✅ NUEVO: Método para enviar IDs a la Blacklist
  static Future<Map<String, dynamic>> addToBlacklist(List<int> animeIds) async {
      try {
          print('🌐 Enviando ${animeIds.length} IDs a la Blacklist API...');
          
          final response = await http.post(
              Uri.parse('$baseUrl/api/blacklist'), // ✅ Nuevo endpoint
              headers: {'Content-Type': 'application/json'},
              body: json.encode({'anime_ids': animeIds}),
          ).timeout(const Duration(seconds: 30));
          
          print('📡 Blacklist Response status: ${response.statusCode}');
          
          final data = json.decode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;

          if (response.statusCode == 200) {
              return data;
          } else {
              throw Exception(data['message'] ?? 'Error al añadir a la blacklist');
          }
      } catch (e) {
          print('❌ Error API Blacklist: $e');
          rethrow;
      }
  }

  static Future<Map<String, dynamic>> getRecommendations(String username) async {
    try {
      print('🌐 Conectando con API: $baseUrl/api/recommendations/$username');
      
      final response = await http.get(
        Uri.parse('$baseUrl/api/recommendations/$username'),
        headers: {'Content-Type': 'application/json'},
      ).timeout(
        const Duration(seconds: 300), // TIMEOUT AUMENTADO A 5 MINUTOS (300s)
        onTimeout: () {
          throw const FormatException('Timeout: La solicitud tardó demasiado en responder.');
        },
      );
      
      print('📡 Response status: ${response.statusCode}');
      
      if (response.statusCode == 200) {
        final data = json.decode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
        
        // GUARDAR DATOS EN CACHÉ DESPUÉS DE UNA LLAMADA EXITOSA
        await _saveDataToCache(username, data);

        return data;
      } else {
        // Intentar decodificar el error si lo hay
        final errorBody = json.decode(utf8.decode(response.bodyBytes));
        throw Exception(errorBody['message'] ?? 'Error del servidor: ${response.statusCode}');
      }
    } catch (e) {
      print('❌ Error API: $e');
      rethrow;
    }
  }

  // --- MÉTODOS DE CACHÉ (SHARED PREFERENCES) ---
  
  // Guardar la respuesta JSON completa de la API
  static Future<void> _saveDataToCache(String username, Map<String, dynamic> data) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final key = '$_storageKeyBase$username';
      final jsonString = json.encode(data);
      await prefs.setString(key, jsonString);
      print('✅ Datos de recomendaciones guardados en caché para $username.');
    } catch (e) {
      print('❌ Error al guardar datos en caché: $e');
    }
  }

  // Cargar los datos de la caché
  static Future<Map<String, dynamic>?> loadDataFromCache(String username) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final key = '$_storageKeyBase$username';
      final jsonString = prefs.getString(key);
      
      if (jsonString != null) {
        print('💡 Datos de recomendaciones cargados desde caché para $username.');
        return json.decode(jsonString) as Map<String, dynamic>;
      }
    } catch (e) {
      print('❌ Error al cargar datos desde caché: $e');
    }
    print('❌ No hay datos guardados en caché para $username.');
    return null;
  }
  
  // ✅ IMPLEMENTACIÓN DEL MÉTODO FALTANTE clearCache
  // Limpia todos los datos de recomendaciones de la caché, independientemente del usuario.
  static Future<void> clearCache() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      // Obtenemos todas las claves y filtramos solo aquellas que almacenan datos de recomendación
      final keysToRemove = prefs.getKeys().where((key) => key.startsWith(_storageKeyBase)).toList();
      
      for (final key in keysToRemove) {
        await prefs.remove(key);
      }
      print('✅ Caché de recomendaciones limpiada. ${keysToRemove.length} entradas eliminadas.');
    } catch (e) {
      print('❌ Error al limpiar la caché de recomendaciones: $e');
    }
  }
}