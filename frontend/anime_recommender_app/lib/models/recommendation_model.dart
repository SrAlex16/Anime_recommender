import 'package:flutter/material.dart';

class AnimeRecommendationsScreen extends StatelessWidget {
  final List<dynamic> recommendations;

  // Constructor con valor por defecto para la ruta con nombre
  const AnimeRecommendationsScreen({
    super.key,
    this.recommendations = const [],
  }); 

  @override
  Widget build(BuildContext context) {
    // Si viene vacío, intentar obtener de los argumentos de ruta
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
                final rec = actualRecommendations[index];
                
                String genresDisplay = '';
                if (rec['genres'] is List) {
                  genresDisplay = (rec['genres'] as List).take(3).join(', '); 
                } else if (rec['genres'] is String) {
                  genresDisplay = (rec['genres'] as String).split(' ').take(3).join(', ');
                }

                final score = (rec['score'] / 10).toStringAsFixed(1);

                return Card(
                  color: const Color(0xFF38476B),
                  margin: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                  child: ListTile(
                    contentPadding: const EdgeInsets.all(10),
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
                          'Puntuación AniList: $score / 10.0',
                          style: const TextStyle(color: Colors.yellow, fontSize: 13),
                        ),
                        Text(
                          'Tipo: ${rec['type'] ?? 'N/A'}',
                          style: const TextStyle(color: Colors.white70, fontSize: 13),
                        ),
                        Text(
                          'Géneros: $genresDisplay',
                          style: const TextStyle(color: Colors.white70, fontSize: 13),
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