// lib/screens/anime_recommendations_screen.dart
import 'package:flutter/material.dart';

class AnimeRecommendationsScreen extends StatelessWidget {
  final List<dynamic> recommendations;
  final Map<String, dynamic> statistics;
  final String Function(String) tr; 

  const AnimeRecommendationsScreen({
    super.key,
    this.recommendations = const [],
    this.statistics = const {},
    required this.tr,
  });

  // --- Funciones Auxiliares de Lógica ---
  
  // Función auxiliar para limpiar la descripción de etiquetas HTML y limitar su longitud
  String _cleanDescription(String description, {int maxLength = 150}) {
    String cleanDesc = description
        .replaceAll(RegExp(r'<br>'), '\n')
        .replaceAll(RegExp(r'<[^>]*>'), '')
        .replaceAll(RegExp(r'\n+'), '\n')
        .trim();
    
    if (cleanDesc.length > maxLength) {
      return '${cleanDesc.substring(0, maxLength)}...';
    }
    return cleanDesc;
  }
  
  // Función auxiliar para formatear los estudios de la lista de strings
  String _formatStudios(dynamic studios) {
    if (studios == null) return tr('common_na');
    if (studios is String) {
      // Limpiar el formato ['studio1', 'studio2']
      return studios.replaceAll(RegExp(r"['\[\]\\]"), '').replaceAll(RegExp(r"\s*,\s*"), ', ');
    }
    if (studios is List) {
      return studios.join(', ');
    }
    return studios.toString();
  }

  // Función auxiliar para formatear los géneros
  String _formatGenres(dynamic genres) {
    if (genres == null) return tr('common_na');
    if (genres is String) {
      return genres.replaceAll(RegExp(r"['\[\]\\]"), '').replaceAll(RegExp(r"\s*,\s*"), ', ');
    }
    if (genres is List) {
      return genres.join(', ');
    }
    return genres.toString();
  }

  // Función auxiliar para formatear los temas (tags)
  String _formatTags(dynamic tags) {
    if (tags == null) return tr('common_na');
    if (tags is String) {
      return tags.replaceAll(RegExp(r"['\[\]\\]"), '').replaceAll(RegExp(r"\s*,\s*"), ', ');
    }
    if (tags is List) {
      return tags.join(', ');
    }
    return tags.toString();
  }

  // --- Widgets Auxiliares de Interfaz ---

  // Elemento individual para el detalle de la tarjeta
  Widget _buildDetailItem(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2.0),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: const TextStyle(fontWeight: FontWeight.w500, color: Colors.white, fontSize: 13),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              value,
              style: const TextStyle(fontSize: 13, color: Colors.white70),
            ),
          ),
        ],
      ),
    );
  }
  
  // Elemento individual para el detalle de estadísticas
  Widget _buildStatItem(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4.0),
      child: RichText(
        text: TextSpan(
          style: const TextStyle(fontSize: 16, color: Colors.white70),
          children: <TextSpan>[
            TextSpan(text: label, style: const TextStyle(fontWeight: FontWeight.bold, color: Colors.white)),
            TextSpan(text: ' $value'),
          ],
        ),
      ),
    );
  }

  // Diálogo para mostrar las estadísticas
void _showStatistics(BuildContext context) {
    showDialog(
      context: context,
      builder: (BuildContext context) {
        return AlertDialog(
          backgroundColor: const Color(0xFF3E497A),
          // ✅ Titulo cambiado a "Estadísticas" usando la nueva clave de traducción
          title: Text(tr('stats_dialog_title'), style: const TextStyle(color: Colors.white)),
          content: SingleChildScrollView(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                // ✅ total_anime_in_list
                _buildStatItem(
                    tr('stats_total_count'), 
                    '${statistics['total_anime_in_list'] ?? tr('common_na')}'
                ),
                // ✅ average_user_score
                _buildStatItem(
                    tr('stats_avg_score'), 
                    '${(statistics['average_user_score'] as num?)?.toStringAsFixed(2) ?? tr('common_na')}' // Formato a 2 decimales
                ),
                // ✅ most_watched_genre
                _buildStatItem(
                    tr('stats_most_watched_genre'), 
                    statistics['most_watched_genre'] ?? tr('common_na')
                ),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: Text(tr('details_close_button'), style: const TextStyle(color: Colors.white70)),
            ),
          ],
        );
      },
    );
  }

  // Diálogo de detalles para cada recomendación
  void _showDetailsDialog(BuildContext context, Map<String, dynamic> rec) {
    
    final fullDescription = (rec['description'] as String? ?? tr('recommendations_description_default'));
    final score = (rec['score'] as num?) ?? 0;
    
    // ✅ Se toma directamente del campo 'Tipo' de la API y se ofrece un fallback por si el nombre de la key cambia.
    // Además, se eliminan los fallbacks de tipo 'format', 'mediaType', 'source' que no son necesarios para tu API actual.
    final animeType = (rec['Tipo'] ?? rec['type'])
        ?.toString()
        .trim();

    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: const Color(0xFF3E497A),
        title: Text(
          rec['title'] ?? tr('recommendations_unknown_title'), 
          style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold)
        ),
        content: SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: <Widget>[
              // ✅ Muestra el campo SÓLO si el valor existe y no es "null" o vacío
              if (animeType != null && animeType.isNotEmpty && animeType != 'null')
                _buildDetailItem(tr('recommendations_type_label'), animeType),
                
              _buildDetailItem(tr('details_episodes_label'), '${rec['episodes'] ?? tr('common_na')}'),
              _buildDetailItem(tr('details_status_label'), rec['status'] ?? tr('common_na')),
              
              // ❌ El campo de fecha de inicio se ha ELIMINADO completamente.
              
              _buildDetailItem(tr('details_studios_label'), _formatStudios(rec['studios'])),
              
              const Divider(color: Colors.white30),
              
              // --- Puntuación y Clasificación ---
              _buildDetailItem(tr('recommendations_score_label'),
                  '${(score / 10.0).toStringAsFixed(1)} / 10.0'),
              _buildDetailItem(tr('recommendations_genres_label'), _formatGenres(rec['genres'])),
              _buildDetailItem(tr('details_tags_label'), _formatTags(rec['tags'])), 
              
              const Divider(color: Colors.white30),
              
              // --- Sinopsis (Al final) ---
              Text(
                tr('details_description_title'),
                style: const TextStyle(
                    fontWeight: FontWeight.bold, color: Colors.white, fontSize: 14),
              ),
              const SizedBox(height: 4),
              Text(
                _cleanDescription(fullDescription, maxLength: 1000).replaceAll('...', ''), 
                style: const TextStyle(fontSize: 13, color: Colors.white70),
              ),
              const SizedBox(height: 16),
            ],
          ),
        ),
        actions: <Widget>[
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: Text(tr('details_close_button'),
                style: const TextStyle(color: Colors.white70)),
          ),
        ],
      ),
    );
  }


  // --- Método Build principal ---

  @override
  Widget build(BuildContext context) {
    final actualRecommendations = recommendations.isNotEmpty 
        ? recommendations 
        : ModalRoute.of(context)?.settings.arguments as List<dynamic>? ?? [];

    return Scaffold(
      backgroundColor: const Color(0xFF4C5E87),
      appBar: AppBar(
        title: Text(tr('recommendations_screen_title'), style: const TextStyle(color: Colors.white)),
        backgroundColor: const Color(0xFF4C5E87),
        elevation: 0,
        iconTheme: const IconThemeData(color: Colors.white),
        actions: [
          IconButton(
            icon: const Icon(Icons.analytics),
            onPressed: () {
              if (statistics.isNotEmpty) {
                _showStatistics(context);
              } else {
                 ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(content: Text(tr('stats_not_available')))
                );
              }
            },
          ),
        ],
      ),
      body: actualRecommendations.isEmpty
          ? Center(
              child: Padding(
                padding: const EdgeInsets.all(32.0),
                child: Text(
                  tr('recommendations_no_found'),
                  textAlign: TextAlign.center,
                  style: const TextStyle(fontSize: 18, color: Colors.white),
                ),
              ),
            )
          : ListView.builder(
              padding: const EdgeInsets.only(top: 10.0),
              itemCount: actualRecommendations.length,
              itemBuilder: (context, index) {
                final rec = actualRecommendations[index] as Map<String, dynamic>;
                final score = (rec['score'] as num?) ?? 0;
                final genresDisplay = _formatGenres(rec['genres']); 
                
                // Lógica de tipo para el subtitle: usa 'Tipo' de la API y 'N/A' como fallback si falta.
                final animeTypeSubtitle = rec['Tipo'] ?? tr('common_na'); 

                return Card(
                  color: const Color(0xFF3E497A),
                  margin: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 8.0),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                  elevation: 4,
                  child: ListTile( 
                    onTap: () => _showDetailsDialog(context, rec),
                    contentPadding: const EdgeInsets.all(10),
                    leading: CircleAvatar(
                      backgroundColor: Colors.orange,
                      radius: 20,
                      child: Text('${index + 1}', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
                    ),
                    title: Text(
                      rec['title'] ?? tr('recommendations_unknown_title'),
                      style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 16),
                    ),
                    subtitle: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const SizedBox(height: 4),
                        Text(
                          '${tr('recommendations_score_label')} ${(score / 10.0).toStringAsFixed(1)} / 10.0',
                          style: const TextStyle(color: Colors.yellow, fontSize: 13),
                        ),
                        Text(
                          '${tr('recommendations_type_label')} ${animeTypeSubtitle}', 
                          style: const TextStyle(color: Colors.white70, fontSize: 13),
                        ),
                        Text(
                          '${tr('recommendations_genres_label')} $genresDisplay',
                          style: const TextStyle(color: Colors.white70, fontSize: 13),
                        ),
                        const SizedBox(height: 8),
                        Text(
                          _cleanDescription(rec['description'] ?? tr('recommendations_description_default')),
                          style: const TextStyle(color: Colors.white54, fontSize: 11),
                        ),
                      ],
                    ),
                  ),
                );
              },
            ),
    );
  }
}