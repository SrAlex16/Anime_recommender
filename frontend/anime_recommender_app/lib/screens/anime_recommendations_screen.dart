// lib/screens/anime_recommendations_screen.dart
import 'package:flutter/material.dart';

class AnimeRecommendationsScreen extends StatelessWidget {
  final List<dynamic> recommendations;
  final Map<String, dynamic> statistics;

  const AnimeRecommendationsScreen({
    super.key,
    this.recommendations = const [],
    this.statistics = const {},
  });

  // Función auxiliar para limpiar la descripción de etiquetas HTML y limitar su longitud
  String _cleanDescription(String description) {
    // Limpiar etiquetas HTML y limitar longitud
    String cleanDesc = description
        .replaceAll(RegExp(r'<br>'), '\n')
        .replaceAll(RegExp(r'<[^>]*>'), '')
        .replaceAll(RegExp(r'\n+'), '\n')
        .trim();
    
    // Limitar a 150 caracteres para la vista principal
    if (cleanDesc.length > 150) {
      return '${cleanDesc.substring(0, 150)}...';
    }
    return cleanDesc;
  }
  
  // Función auxiliar para formatear los estudios de la lista de strings
  String _formatStudios(dynamic studios) {
    if (studios == null) return 'N/A';
    if (studios is String) {
      // Limpiar el formato ['studio1', 'studio2'] de la respuesta
      return studios.replaceAll(RegExp(r"\['|'\]"), '').replaceAll(RegExp(r"'\s*,\s*'"), ', ');
    }
    return studios.toString();
  }

  // --- Widgets Auxiliares ---

  // Diálogo para mostrar las estadísticas
  void _showStatistics(BuildContext context) {
    showDialog(
      context: context,
      builder: (BuildContext context) {
        return AlertDialog(
          backgroundColor: const Color(0xFF3E497A),
          title: const Text('Estadísticas del Usuario', style: TextStyle(color: Colors.white)),
          content: SingleChildScrollView(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                _buildStatItem('Anime en lista de MAL:', '${statistics['total_anime_in_list'] ?? 'N/A'}'),
                _buildStatItem('Género más visto:', statistics['most_watched_genre'] ?? 'N/A'),
                _buildStatItem('Puntuación promedio (MAL):', '${(statistics['average_user_score'] as num?)?.toStringAsFixed(2) ?? 'N/A'} / 10.0'),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('Cerrar', style: TextStyle(color: Colors.white70)),
            ),
          ],
        );
      },
    );
  }

  // Elemento individual para las estadísticas
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

  // Diálogo de detalles para cada recomendación
  void _showAnimeDetails(BuildContext context, Map<String, dynamic> rec) {
    // Usar la descripción original sin truncar
    final fullDescription = (rec['description'] as String? ?? 'No disponible.');
    // Usar los géneros del campo "genres" que viene más limpio
    final genresDisplay = (rec['genres'] as String? ?? 'N/A').replaceAll(' ', ', ');
    
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: const Color(0xFF3E497A),
        title: Text(rec['title'] ?? 'Título Desconocido', 
          style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold)
        ),
        content: SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: <Widget>[
              _buildDetailItem('Tipo:', rec['Tipo'] ?? 'N/A'),
              _buildDetailItem('Episodios:', '${rec['episodes'] ?? 'N/A'}'),
              _buildDetailItem('Estado:', rec['status'] ?? 'N/A'),
              _buildDetailItem('Estudios:', _formatStudios(rec['studios'])),
              const Divider(color: Colors.white30),
              _buildDetailItem('Puntuación AniList:', '${(rec['score'] as num?) ?? 'N/A'}%'),
              _buildDetailItem('Géneros:', genresDisplay),
              const Divider(color: Colors.white30),
              const Text('Sinopsis:', style: TextStyle(fontWeight: FontWeight.bold, color: Colors.white, fontSize: 14)),
              const SizedBox(height: 4),
              Text(_cleanDescription(fullDescription).replaceAll('...', ''), // Limpiar solo el formato, sin truncar
                style: const TextStyle(fontSize: 13, color: Colors.white70),
              ),
              const SizedBox(height: 16),
            ],
          ),
        ),
        actions: <Widget>[
          TextButton(
            onPressed: () {
              // Aquí podrías abrir el enlace en el navegador usando url_launcher
              // final url = rec['siteUrl'];
              // if (url != null) launchUrlString(url);
              Navigator.pop(context);
            },
            child: const Text('Ver en AniList', style: TextStyle(color: Colors.white)),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cerrar', style: TextStyle(color: Colors.white70)),
          ),
        ],
      ),
    );
  }

  // Elemento individual para el detalle del anime
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

  // --- Método Build principal ---

  @override
  Widget build(BuildContext context) {
    // Usamos las propiedades, ya que LoginScreen las pasa directamente. 
    // Mantenemos la lógica de argumentos por si se navega con rutas nombradas.
    final actualRecommendations = recommendations.isNotEmpty 
        ? recommendations 
        : ModalRoute.of(context)?.settings.arguments as List<dynamic>? ?? [];

    return Scaffold(
      backgroundColor: const Color(0xFF4C5E87),
      appBar: AppBar(
        title: const Text('Recomendaciones de Anime', style: TextStyle(color: Colors.white)),
        backgroundColor: const Color(0xFF4C5E87),
        elevation: 0,
        iconTheme: const IconThemeData(color: Colors.white),
        actions: [
          IconButton(
            icon: const Icon(Icons.analytics),
            onPressed: () {
              // Mostrar estadísticas solo si existen datos
              if (statistics.isNotEmpty) {
                _showStatistics(context);
              } else {
                 ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('Estadísticas no disponibles'))
                );
              }
            },
          ),
        ],
      ),
      body: actualRecommendations.isEmpty
          ? const Center(
              child: Padding(
                padding: EdgeInsets.all(32.0),
                child: Text(
                  'No se encontraron recomendaciones.',
                  textAlign: TextAlign.center,
                  style: TextStyle(fontSize: 18, color: Colors.white),
                ),
              ),
            )
          : ListView.builder(
              padding: const EdgeInsets.only(top: 10.0),
              itemCount: actualRecommendations.length,
              itemBuilder: (context, index) {
                final rec = actualRecommendations[index] as Map<String, dynamic>;
                final score = (rec['score'] as num?) ?? 0;
                final genresDisplay = (rec['genres'] as String? ?? 'N/A').replaceAll(' ', ', ');

                return Card(
                  color: const Color(0xFF3E497A),
                  margin: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 8.0),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                  elevation: 4,
                  child: ListTile(
                    contentPadding: const EdgeInsets.all(10),
                    onTap: () => _showAnimeDetails(context, rec), // Abrir detalles al tocar
                    leading: CircleAvatar(
                      backgroundColor: Colors.orange,
                      radius: 20,
                      child: Text('${index + 1}', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
                    ),
                    title: Text(
                      rec['title'] ?? 'Título Desconocido',
                      style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 16),
                    ),
                    subtitle: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const SizedBox(height: 4),
                        Text(
                          'Puntuación AniList: ${(score / 10.0).toStringAsFixed(1)} / 10.0', // Se divide entre 10 para coincidir con la escala de la imagen
                          style: const TextStyle(color: Colors.yellow, fontSize: 13),
                        ),
                        Text(
                          'Tipo: ${rec['Tipo'] ?? 'N/A'}',
                          style: const TextStyle(color: Colors.white70, fontSize: 13),
                        ),
                        Text(
                          'Géneros: $genresDisplay',
                          style: const TextStyle(color: Colors.white70, fontSize: 13),
                        ),
                        const SizedBox(height: 8),
                        Text(
                          _cleanDescription(rec['description'] ?? 'Sinopsis no disponible.'),
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