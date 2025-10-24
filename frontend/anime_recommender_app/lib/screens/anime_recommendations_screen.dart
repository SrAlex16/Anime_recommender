// lib/screens/anime_recommendations_screen.dart
import 'package:flutter/material.dart';
import '../services/api_service.dart'; // ✅ Importar el servicio API

// 1. Convertimos a StatefulWidget para gestionar el estado de selección
class AnimeRecommendationsScreen extends StatefulWidget {
  final List<dynamic> recommendations;
  final Map<String, dynamic> statistics;
  final String Function(String) tr; 

  const AnimeRecommendationsScreen({
    super.key,
    this.recommendations = const [],
    this.statistics = const {},
    required this.tr,
  });

  @override
  State<AnimeRecommendationsScreen> createState() => _AnimeRecommendationsScreenState();
}

class _AnimeRecommendationsScreenState extends State<AnimeRecommendationsScreen> with SingleTickerProviderStateMixin {
  
  final Set<int> _selectedRecIds = {};
  late List<dynamic> _recommendations;
  
  // 💡 AnimationController para la animación del check
  late AnimationController _animationController;
  late Animation<double> _iconScaleAnimation;


  @override
  void initState() {
    super.initState();
    // Inicializamos la lista de recomendaciones desde los argumentos o el constructor.
    _recommendations = widget.recommendations.isNotEmpty 
        ? List.from(widget.recommendations) 
        : ModalRoute.of(context)?.settings.arguments as List<dynamic>? ?? [];

    _animationController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 300),
    );
    // Animación de escala para el efecto de "pop" del check
    _iconScaleAnimation = Tween<double>(begin: 0.8, end: 1.2).animate(
      CurvedAnimation(
        parent: _animationController,
        curve: Curves.elasticOut,
      ),
    );
  }

  @override
  void dispose() {
    _animationController.dispose();
    super.dispose();
  }

  // --- Funciones Auxiliares de Lógica (Mantenidas) ---
  
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
  
  String _formatStudios(dynamic studios) {
    if (studios == null) return widget.tr('common_na');
    if (studios is String) {
      return studios.replaceAll(RegExp(r"['\[\]\\]"), '').replaceAll(RegExp(r"\s*,\s*"), ', ');
    }
    if (studios is List) {
      return studios.join(', ');
    }
    return studios.toString();
  }

  String _formatGenres(dynamic genres) {
    if (genres == null) return widget.tr('common_na');
    if (genres is String) {
      return genres.replaceAll(RegExp(r"['\[\]\\]"), '').replaceAll(RegExp(r"\s*,\s*"), ', ');
    }
    if (genres is List) {
      return genres.join(', ');
    }
    return genres.toString();
  }

  String _formatTags(dynamic tags) {
    if (tags == null) return widget.tr('common_na');
    if (tags is String) {
      return tags.replaceAll(RegExp(r"['\[\]\\]"), '').replaceAll(RegExp(r"\s*,\s*"), ', ');
    }
    if (tags is List) {
      return tags.join(', ');
    }
    return tags.toString();
  }


  // --- Lógica de Blacklist ---

  void _toggleSelection(Map<String, dynamic> rec) {
    // Usamos AniListID o MAL_ID como identificador único
    final id = rec['AniListID'] as int? ?? rec['MAL_ID'] as int?;
    if (id == null) return;

    setState(() {
      if (_selectedRecIds.contains(id)) {
        _selectedRecIds.remove(id);
      } else {
        _selectedRecIds.add(id);
        // 💡 Ejecutar la animación al seleccionar
        _animationController.forward(from: 0.0);
      }
    });
  }

  Future<void> _blacklistSelectedItems() async {
    if (_selectedRecIds.isEmpty) return;

    final List<int> idsToBlacklist = _selectedRecIds.toList();
    final int count = idsToBlacklist.length;
    
    // Mostramos un indicador de carga
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(widget.tr('blacklist_sending')))
    );

    try {
        // 1. Llamar a la API para guardar los IDs en el backend
        await ApiService.addToBlacklist(idsToBlacklist);
        
        // 2. Filtrar la lista local
        final List<dynamic> remainingRecs = [];
        
        for (var rec in _recommendations) {
            final id = rec['AniListID'] as int? ?? rec['MAL_ID'] as int?;
            if (id != null && !_selectedRecIds.contains(id)) {
                remainingRecs.add(rec);
            }
        }
        
        setState(() {
            _recommendations = remainingRecs;
            _selectedRecIds.clear(); 
        });

        ScaffoldMessenger.of(context).hideCurrentSnackBar();
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(widget.tr('blacklist_confirmation').replaceFirst('Animes', '$count Animes')),
            backgroundColor: Colors.green,
          )
        );

    } catch (e) {
        ScaffoldMessenger.of(context).hideCurrentSnackBar();
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(widget.tr('blacklist_error') + (e is Exception ? e.toString() : 'Error desconocido')),
            backgroundColor: Colors.red,
          )
        );
    }
  }


  // --- Widgets Auxiliares (Omitidos por brevedad, mantienen la lógica anterior) ---
  
  Widget _buildDetailItem(String label, String value) {
    // ... (implementación anterior)
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
  
  Widget _buildStatItem(String label, String value) {
    // ... (implementación anterior)
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

  void _showStatistics(BuildContext context) {
    // ... (implementación anterior)
    showDialog(
      context: context,
      builder: (BuildContext context) {
        return AlertDialog(
          backgroundColor: const Color(0xFF3E497A),
          title: Text(widget.tr('stats_dialog_title'), style: const TextStyle(color: Colors.white)),
          content: SingleChildScrollView(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                _buildStatItem(
                    widget.tr('stats_total_count'), 
                    '${widget.statistics['total_anime_in_list'] ?? widget.tr('common_na')}'
                ),
                _buildStatItem(
                    widget.tr('stats_avg_score'), 
                    '${(widget.statistics['average_user_score'] as num?)?.toStringAsFixed(2) ?? widget.tr('common_na')}'
                ),
                _buildStatItem(
                    widget.tr('stats_most_watched_genre'), 
                    widget.statistics['most_watched_genre'] ?? widget.tr('common_na')
                ),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: Text(widget.tr('details_close_button'), style: const TextStyle(color: Colors.white70)),
            ),
          ],
        );
      },
    );
  }

  void _showDetailsDialog(BuildContext context, Map<String, dynamic> rec) {
    // ... (implementación anterior)
    final fullDescription = (rec['description'] as String? ?? widget.tr('recommendations_description_default'));
    final score = (rec['score'] as num?) ?? 0;
    
    final animeType = (rec['Tipo'] ?? rec['type'])?.toString().trim();

    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: const Color(0xFF3E497A),
        title: Text(
          rec['title'] ?? widget.tr('recommendations_unknown_title'), 
          style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold)
        ),
        content: SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: <Widget>[
              if (animeType != null && animeType.isNotEmpty && animeType != 'null')
                _buildDetailItem(widget.tr('recommendations_type_label'), animeType),
                
              _buildDetailItem(widget.tr('details_episodes_label'), '${rec['episodes'] ?? widget.tr('common_na')}'),
              _buildDetailItem(widget.tr('details_status_label'), rec['status'] ?? widget.tr('common_na')),
              _buildDetailItem(widget.tr('details_studios_label'), _formatStudios(rec['studios'])),
              
              const Divider(color: Colors.white30),
              
              _buildDetailItem(widget.tr('recommendations_score_label'),
                  '${(score / 10.0).toStringAsFixed(1)} / 10.0'),
              _buildDetailItem(widget.tr('recommendations_genres_label'), _formatGenres(rec['genres'])),
              _buildDetailItem(widget.tr('details_tags_label'), _formatTags(rec['tags'])), 
              
              const Divider(color: Colors.white30),
              
              Text(
                widget.tr('details_description_title'),
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
            child: Text(widget.tr('details_close_button'),
                style: const TextStyle(color: Colors.white70)),
          ),
        ],
      ),
    );
  }


  // --- Método Build principal ---

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF4C5E87),
      appBar: AppBar(
        title: Text(widget.tr('recommendations_screen_title'), style: const TextStyle(color: Colors.white)),
        backgroundColor: const Color(0xFF4C5E87),
        elevation: 0,
        iconTheme: const IconThemeData(color: Colors.white),
        actions: [
          // ✅ Botón de Blacklist (aparece si hay animes seleccionados)
          if (_selectedRecIds.isNotEmpty)
            IconButton(
              icon: Icon(Icons.playlist_remove, color: Colors.red.shade400),
              tooltip: widget.tr('blacklist_button'),
              onPressed: _blacklistSelectedItems,
            ),
          
          // Botón de Estadísticas
          IconButton(
            icon: const Icon(Icons.analytics),
            onPressed: () {
              if (widget.statistics.isNotEmpty) {
                _showStatistics(context);
              } else {
                 ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(content: Text(widget.tr('stats_not_available')))
                );
              }
            },
          ),
        ],
      ),
      body: _recommendations.isEmpty
          ? Center(
              child: Padding(
                padding: const EdgeInsets.all(32.0),
                child: Text(
                  widget.tr('recommendations_no_found'),
                  textAlign: TextAlign.center,
                  style: const TextStyle(fontSize: 18, color: Colors.white),
                ),
              ),
            )
          : ListView.builder(
              padding: const EdgeInsets.only(top: 10.0),
              itemCount: _recommendations.length,
              itemBuilder: (context, index) {
                final rec = _recommendations[index] as Map<String, dynamic>;
                final score = (rec['score'] as num?) ?? 0;
                final genresDisplay = _formatGenres(rec['genres']); 
                final animeTypeSubtitle = rec['Tipo'] ?? widget.tr('common_na'); 

                final id = rec['AniListID'] as int? ?? rec['MAL_ID'] as int?;
                final isSelected = id != null && _selectedRecIds.contains(id);

                return Card(
                  color: const Color(0xFF3E497A),
                  margin: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 8.0),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                  elevation: 4,
                  child: ListTile( 
                    onTap: () => _showDetailsDialog(context, rec),
                    contentPadding: const EdgeInsets.all(10),
                    // ✅ CircleAvatar modificado para selección con animación
                    leading: GestureDetector(
                      onTap: id != null ? () => _toggleSelection(rec) : null,
                      child: CircleAvatar(
                        backgroundColor: isSelected ? Colors.red.shade400 : Colors.orange,
                        radius: 20,
                        child: isSelected
                            ? ScaleTransition(
                                scale: _iconScaleAnimation,
                                child: const Icon(Icons.check, color: Colors.white, size: 20),
                              )
                            : Text(
                                '${index + 1}', 
                                style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold)
                              ),
                      ),
                    ),
                    title: Text(
                      rec['title'] ?? widget.tr('recommendations_unknown_title'),
                      style: TextStyle(
                        color: Colors.white, 
                        fontWeight: FontWeight.bold, 
                        fontSize: 16,
                        decoration: isSelected ? TextDecoration.lineThrough : TextDecoration.none, // Efecto visual de selección
                        decorationColor: Colors.white70,
                      ),
                    ),
                    subtitle: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const SizedBox(height: 4),
                        Text(
                          '${widget.tr('recommendations_score_label')} ${(score / 10.0).toStringAsFixed(1)} / 10.0',
                          style: const TextStyle(color: Colors.yellow, fontSize: 13),
                        ),
                        Text(
                          '${widget.tr('recommendations_type_label')} ${animeTypeSubtitle}', 
                          style: const TextStyle(color: Colors.white70, fontSize: 13),
                        ),
                        Text(
                          '${widget.tr('recommendations_genres_label')} $genresDisplay',
                          style: const TextStyle(color: Colors.white70, fontSize: 13),
                        ),
                        const SizedBox(height: 8),
                        Text(
                          _cleanDescription(rec['description'] ?? widget.tr('recommendations_description_default')),
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