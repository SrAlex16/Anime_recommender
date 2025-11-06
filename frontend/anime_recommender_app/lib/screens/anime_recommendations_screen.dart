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
    
    _iconScaleAnimation = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(parent: _animationController, curve: Curves.easeOutBack),
    );
  }

  @override
  void dispose() {
    _animationController.dispose();
    super.dispose();
  }

  String _cleanDescription(String htmlString) {
    // Implementación para limpiar HTML (asumida para completar el archivo)
    String text = htmlString.replaceAll(RegExp(r'<[^>]*>|&[^;]+;'), '');
    return text.replaceAll(RegExp(r'\n+'), '\n').trim();
  }

  String _formatList(List<dynamic>? list) {
    if (list == null || list.isEmpty) return 'N/A';
    // Limitar a 3 géneros para el display
    final effectiveList = list.take(3).toList();
    return effectiveList.join(', ');
  }

  void _toggleSelection(int animeId) {
    setState(() {
      if (_selectedRecIds.contains(animeId)) {
        _selectedRecIds.remove(animeId);
        _animationController.reverse();
      } else {
        _selectedRecIds.add(animeId);
        _animationController.forward(from: 0.0);
      }
    });
  }

  Future<void> _addToBlacklist() async {
    if (_selectedRecIds.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(widget.tr('recommendations_error_no_selection'))),
      );
      return;
    }

    final animeIds = _selectedRecIds.toList();

    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (BuildContext context) {
        return AlertDialog(
          content: Row(
            children: [
              const CircularProgressIndicator(),
              const SizedBox(width: 20),
              Text(widget.tr('recommendations_blacklist_loading')),
            ],
          ),
        );
      },
    );

    try {
      final result = await ApiService.addToBlacklist(animeIds);
      
      // Ocultar loader
      if (Navigator.of(context).canPop()) {
        Navigator.of(context).pop();
      }

      if (result['status'] == 'success') {
        // Eliminar los animes seleccionados de la lista local
        setState(() {
          _recommendations.removeWhere((rec) {
            // Es crucial hacer el casting seguro aquí también
            final Map<String, dynamic> recMap = rec as Map<String, dynamic>;
            return _selectedRecIds.contains(recMap['id'] as int?);
          });
          _selectedRecIds.clear(); // Limpiar la selección
        });

        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            // ✅ CORRECCIÓN: Interpolación de cadena para incluir el conteo
            content: Text(
              '${widget.tr('recommendations_blacklist_success')} ${animeIds.length}' 
            ),
            backgroundColor: Colors.green,
          ),
        );
      } else {
        throw Exception(result['message'] ?? widget.tr('recommendations_blacklist_error_default'));
      }
    } catch (e) {
      // Ocultar loader
      if (Navigator.of(context).canPop()) {
        Navigator.of(context).pop();
      }
      
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('${widget.tr('recommendations_blacklist_error')} $e'),
          backgroundColor: Colors.red,
        ),
      );
    }
  }

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
          // Botón para la Blacklist
          IconButton(
            icon: Icon(Icons.block, 
              color: _selectedRecIds.isNotEmpty ? Colors.redAccent : Colors.white54
            ),
            onPressed: _addToBlacklist,
            tooltip: widget.tr('recommendations_blacklist_tooltip'),
          ),
        ],
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(40.0),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 8.0),
            child: Text(
              '${widget.tr('recommendations_total_count')} ${_recommendations.length}',
              style: const TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold),
            ),
          ),
        ),
      ),
      body: _recommendations.isEmpty
          ? Center(
              child: Padding(
                padding: const EdgeInsets.all(32.0),
                child: Text(
                  widget.tr('recommendations_none_found'),
                  textAlign: TextAlign.center,
                  style: const TextStyle(fontSize: 18, color: Colors.white),
                ),
              ),
            )
          : ListView.builder(
              padding: const EdgeInsets.only(top: 10.0),
              itemCount: _recommendations.length,
              itemBuilder: (context, index) {
                // Castear explícitamente a Map<String, dynamic>
                final Map<String, dynamic> rec = _recommendations[index] as Map<String, dynamic>; 
                
                final int animeId = rec['id'] as int? ?? 0;
                final bool isSelected = _selectedRecIds.contains(animeId);
                
                final score = rec['averageScore'] ?? 0;
                final rawGenres = rec['genres'] as List<dynamic>? ?? [];
                final genresDisplay = _formatList(rawGenres);
                final animeTypeSubtitle = rec['type'] ?? 'N/A';
                
                return Card(
                  color: isSelected ? const Color(0xFF3E497A).withOpacity(0.9) : const Color(0xFF5D709D),
                  elevation: 4,
                  margin: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(15),
                    side: isSelected ? const BorderSide(color: Colors.redAccent, width: 2) : BorderSide.none,
                  ),
                  child: ListTile(
                    onTap: () => _toggleSelection(animeId),
                    contentPadding: const EdgeInsets.all(10),
                    leading: Stack(
                      alignment: Alignment.center,
                      children: [
                        CircleAvatar(
                          backgroundColor: isSelected ? Colors.redAccent : const Color(0xFF3E497A),
                          radius: 20,
                          child: Text('${index + 1}', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
                        ),
                        if (isSelected)
                          ScaleTransition(
                            scale: _iconScaleAnimation,
                            child: const Icon(
                              Icons.check_circle,
                              color: Colors.yellow,
                              size: 40,
                            ),
                          ),
                      ],
                    ),
                    title: Text(
                      rec['title'] ?? widget.tr('recommendations_title_default'),
                      style: TextStyle(
                        color: isSelected ? Colors.white : Colors.white, 
                        fontWeight: FontWeight.bold, 
                        fontSize: 16,
                        decoration: isSelected ? TextDecoration.underline : null, // Efecto visual de selección
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