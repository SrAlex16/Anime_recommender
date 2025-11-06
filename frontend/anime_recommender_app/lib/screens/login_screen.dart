// lib/screens/login_screen.dart (Contenido completo - Asegúrate de reemplazar la función de navegación)

import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'anime_recommendations_screen.dart';
import '../services/python_runner.dart';
import '../services/api_service.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen>
    with SingleTickerProviderStateMixin {
  final TextEditingController _usernameController = TextEditingController();
  final FocusNode _usernameFocus = FocusNode();

  bool _isUserSaved = false;
  List<String> _savedUsers = [];
  Map<String, dynamic> _localizedTexts = {};
  String _language = 'es';
  static const int _maxSuggestions = 5;

  late AnimationController _drawerController;
  bool _isDragging = false; // Para detectar si está deslizando

  final Map<String, Map<String, String>> _fallback = {
    'es': {
      'clear_data': 'Borrar datos',
      'data_cleared': 'Datos borrados correctamente',
      'enter_username': 'Introduce tu nombre de usuario de MyAnimeList',
      'get_results': 'Obtener Resultados',
      'save_user': 'Guardar usuario',
      'login_failed': 'Fallo en la conexión/API',
      'login_error': 'No se pudo conectar con el servicio o la API devolvió un error. Revisa los logs de la consola.',
      'user_saved': 'Usuario guardado',
      'username_empty': 'El nombre de usuario no puede estar vacío.',
      'suggestions_title': 'Usuarios Recientes',
      'language_label': 'Español',
      'fetching_recommendations': 'Generando recomendaciones...',
      'generating_message': 'Esto puede tardar unos minutos, por favor sé paciente mientras se entrena el modelo...',
    },
    'en': {
      'clear_data': 'Clear data',
      'data_cleared': 'Data cleared successfully',
      'enter_username': 'Enter your MyAnimeList username',
      'get_results': 'Get Results',
      'save_user': 'Save User',
      'login_failed': 'Connection/API Failed',
      'login_error': 'Could not connect to the service or the API returned an error. Check console logs.',
      'user_saved': 'User saved',
      'username_empty': 'Username cannot be empty.',
      'suggestions_title': 'Recent Users',
      'language_label': 'English',
      'fetching_recommendations': 'Generating recommendations...',
      'generating_message': 'This may take a few minutes, please be patient while the model is trained...',
    },
  };

  @override
  void initState() {
    super.initState();
    _loadLanguage();
    _loadSavedUsers();
    _drawerController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 250),
    );
  }

  // Traducción simple basada en el idioma actual
  String _translate(String key) {
    return _localizedTexts[_language]?[key] ?? _fallback[_language]?[key] ?? _fallback['en']?[key] ?? key;
  }

  Future<void> _loadLanguage() async {
    final prefs = await SharedPreferences.getInstance();
    setState(() {
      _language = prefs.getString('language') ?? 'es';
    });
    await _loadLocalizedTexts(_language);
  }

  Future<void> _loadLocalizedTexts(String lang) async {
    try {
      final jsonString = await rootBundle.loadString('assets/i18n/$lang.json');
      setState(() {
        _localizedTexts = json.decode(jsonString);
      });
    } catch (e) {
      print('Error loading localization for $lang: $e');
      _localizedTexts = _fallback;
    }
  }

  Future<void> _toggleLanguage() async {
    final newLanguage = (_language == 'es') ? 'en' : 'es';
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('language', newLanguage);
    await _loadLocalizedTexts(newLanguage);
    setState(() {
      _language = newLanguage;
    });
  }

  // --- Lógica de usuarios guardados ---
  Future<void> _loadSavedUsers() async {
    final prefs = await SharedPreferences.getInstance();
    setState(() {
      _savedUsers = prefs.getStringList('saved_users') ?? [];
    });
    if (_savedUsers.isNotEmpty) {
      _usernameController.text = _savedUsers.first;
    }
  }

  Future<void> _saveUser(String username) async {
    final prefs = await SharedPreferences.getInstance();
    _savedUsers.remove(username); // Eliminar si ya existe
    _savedUsers.insert(0, username); // Insertar al principio
    if (_savedUsers.length > _maxSuggestions) {
      _savedUsers = _savedUsers.sublist(0, _maxSuggestions);
    }
    await prefs.setStringList('saved_users', _savedUsers);
    setState(() {
      _isUserSaved = true;
    });
    // Mostrar snackbar de éxito
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(_translate('user_saved'))),
      );
    }
  }

  // --- Lógica de navegación y API ---
  void _navigateToRecommendations({required String username, required Map<String, dynamic> apiResult}) {
    // 💡 SOLUCIÓN CRÍTICA: Extraer los datos de forma segura
    // Usar ?? [] y ?? {} para evitar el _TypeError al pasar null a un campo no nulo.
    final List<dynamic> recommendations = apiResult['recommendations'] as List<dynamic>? ?? [];
    final Map<String, dynamic> statistics = apiResult['statistics'] as Map<String, dynamic>? ?? {};

    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (context) => AnimeRecommendationsScreen(
          // Pasar las variables que ya están garantizadas como no nulas
          recommendations: recommendations,
          statistics: statistics, 
          tr: (key) => _translate(key),
        ),
      ),
    );
  }


  Future<void> _handleLogin() async {
    final username = _usernameController.text.trim();
    if (username.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(_translate('username_empty'))),
      );
      return;
    }

    // 1. Mostrar diálogo de carga
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) => AlertDialog(
        title: Text(_translate('fetching_recommendations')),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const CircularProgressIndicator(),
            const SizedBox(height: 15),
            Text(_translate('generating_message')),
          ],
        ),
      ),
    );

    // 2. Llamar a la API
    try {
      final apiResult = await PythonRunner.runTrainModel(username: username);

      // 3. Cerrar diálogo de carga y navegar
      if (mounted) {
        Navigator.of(context).pop(); // Cerrar el diálogo
        _navigateToRecommendations(username: username, apiResult: apiResult);
      }

    } catch (e) {
      print('❌ ERROR EN _handleLogin: $e');
      // 4. Cerrar diálogo de carga y mostrar error
      if (mounted) {
        Navigator.of(context).pop(); // Cerrar el diálogo
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('${_translate('login_failed')}: ${e.toString()}'),
            backgroundColor: Colors.red,
            duration: const Duration(seconds: 5),
          ),
        );
      }
    }
  }
  // --- Fin Lógica de navegación y API ---


  // --- OTRAS FUNCIONES ---
  Future<void> _clearAllData() async {
    final prefs = await SharedPreferences.getInstance();
    // Limpiar caché de recomendaciones y usuarios guardados
    await ApiService.clearCache();
    await prefs.remove('saved_users');
    await prefs.remove('language');

    setState(() {
      _savedUsers = [];
      _usernameController.clear();
      _isUserSaved = false;
      _language = 'es';
    });

    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(_translate('data_cleared'))),
      );
    }
  }


  // --- WIDGETS ---
  // ... (El resto del código de build() y widgets del drawer, etc., sigue igual) ...
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Anime Recommender'),
        backgroundColor: Colors.blueGrey[900],
        foregroundColor: Colors.white,
      ),
      backgroundColor: Colors.blueGrey[800],
      endDrawer: Builder(
        builder: (context) {
          return GestureDetector(
            onHorizontalDragStart: (details) {
              if (details.localPosition.dx > 200) {
                _isDragging = true;
              }
            },
            onHorizontalDragUpdate: (details) {
              if (_isDragging && _drawerController.value > 0) {
                // Controlar el deslizamiento del drawer
                final dragExtent = details.primaryDelta! / 300; // Normalizar el valor
                _drawerController.value -= dragExtent;
              }
            },
            onHorizontalDragEnd: (details) {
              if (_isDragging) {
                // Si la velocidad es alta, cerrar/abrir, sino restaurar
                if (details.velocity.pixelsPerSecond.dx < -500) {
                  _drawerController.forward();
                } else if (details.velocity.pixelsPerSecond.dx > 500) {
                  _drawerController.reverse();
                } else {
                  if (_drawerController.value > 0.5) {
                    _drawerController.forward();
                  } else {
                    _drawerController.reverse();
                  }
                }
              }
              _isDragging = false;
            },
            child: Drawer(
              child: Container(
                color: Colors.blueGrey[900],
                child: Padding(
                  padding: const EdgeInsets.only(top: 40.0),
                  child: ListView(
                    padding: EdgeInsets.zero,
                    children: [
                      // Encabezado del Drawer
                      Padding(
                        padding: const EdgeInsets.all(16.0),
                        child: Text(
                          'Ajustes',
                          style: TextStyle(
                            color: Colors.white,
                            fontSize: 24,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ),
                      const Divider(color: Colors.white38),
                      // Opción Borrar datos
                      ListTile(
                        leading: const Padding(
                          padding: EdgeInsets.only(left: 4.0),
                          child: Icon(Icons.delete_forever, color: Colors.redAccent),
                        ),
                        title: Text(
                          _translate('clear_data'),
                          style: const TextStyle(
                            color: Colors.redAccent,
                            fontSize: 18,
                          ),
                        ),
                        onTap: () async {
                          _drawerController.reverse();
                          await Future.delayed(const Duration(milliseconds: 200));
                          await _clearAllData();
                        },
                      ),
                      const Divider(color: Colors.white38),
                      // Opción Cambiar idioma
                      ListTile(
                        leading: const Padding(
                          padding: EdgeInsets.only(left: 4.0),
                          child: Icon(Icons.language, color: Colors.white),
                        ),
                        title: FittedBox(
                          fit: BoxFit.scaleDown,
                          alignment: Alignment.centerLeft,
                          child: Text(
                            (_language == 'es')
                                ? (_localizedTexts['en']?['language_label'] ?? 'English')
                                : (_localizedTexts['es']?['language_label'] ?? 'Español'),
                            style: const TextStyle(
                              color: Colors.white,
                              fontSize: 18,
                            ),
                            maxLines: 1,
                            overflow: TextOverflow.visible,
                          ),
                        ),
                        onTap: () async {
                          _drawerController.reverse();
                          await Future.delayed(const Duration(milliseconds: 200));
                          await _toggleLanguage();
                        },
                      ),
                    ],
                  ),
                ),
              ),
            ),
          );
        },
      ),
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(32.0),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Título principal
              const Text(
                'Anime Recommender',
                textAlign: TextAlign.center,
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 32,
                  fontWeight: FontWeight.bold,
                  shadows: [
                    Shadow(
                      blurRadius: 10.0,
                      color: Colors.black54,
                      offset: Offset(2.0, 2.0),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 40),
              // Campo de texto
              Autocomplete<String>(
                optionsBuilder: (TextEditingValue textEditingValue) {
                  if (textEditingValue.text.isEmpty) {
                    // Mostrar sugerencias de usuarios guardados
                    return _savedUsers.take(_maxSuggestions);
                  }
                  // Filtrar usuarios guardados
                  return _savedUsers.where((String option) {
                    return option.toLowerCase().contains(textEditingValue.text.toLowerCase());
                  }).take(_maxSuggestions);
                },
                fieldViewBuilder: (context, textController, focusNode, onFieldSubmitted) {
                  // NO hacemos _usernameController.value = ... (ya está enlazado)
                  // NO hacemos _usernameFocus.value = ... (FocusNode no tiene setter 'value')
                  
                  // Simplemente retornamos el TextField usando los controladores/nodos provistos
                  return TextField(
                    controller: textController, // ✅ Usar el textController provisto
                    focusNode: focusNode,     // ✅ Usar el focusNode provisto
                    decoration: InputDecoration(
                      hintText: _translate('enter_username'),
                      // ... (resto de la decoración) ...
                    ),
                    style: const TextStyle(color: Colors.white),
                    onSubmitted: (_) => _handleLogin(),
                  );
                },
                
                onSelected: (String selection) { /* ... */ },
              ),
              const SizedBox(height: 20),
              // Botón de Login
              ElevatedButton.icon(
                onPressed: _handleLogin,
                icon: const Icon(Icons.recommend),
                label: Text(
                  _translate('get_results'),
                  style: const TextStyle(fontSize: 18),
                ),
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.teal,
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(vertical: 15),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                  elevation: 5,
                ),
              ),
              const SizedBox(height: 20),
              // Botón de Guardar Usuario
              OutlinedButton.icon(
                onPressed: () {
                  final username = _usernameController.text.trim();
                  if (username.isNotEmpty) {
                    _saveUser(username);
                  } else {
                    ScaffoldMessenger.of(context).showSnackBar(
                      SnackBar(content: Text(_translate('username_empty'))),
                    );
                  }
                },
                icon: const Icon(Icons.bookmark_border),
                label: Text(
                  _translate('save_user'),
                  style: const TextStyle(fontSize: 16),
                ),
                style: OutlinedButton.styleFrom(
                  foregroundColor: Colors.white,
                  side: const BorderSide(color: Colors.white70),
                  padding: const EdgeInsets.symmetric(vertical: 15),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                ),
              ),
              const SizedBox(height: 20),
              // Sugerencias de usuarios (si las hay)
              if (_savedUsers.length > 1) ...[
                Text(
                  _translate('suggestions_title'),
                  textAlign: TextAlign.center,
                  style: const TextStyle(color: Colors.white70, fontSize: 14, fontStyle: FontStyle.italic),
                ),
                const SizedBox(height: 8),
                Wrap(
                  alignment: WrapAlignment.center,
                  spacing: 8.0,
                  runSpacing: 4.0,
                  children: _savedUsers.sublist(1).map((user) {
                    return ActionChip(
                      label: Text(user, style: const TextStyle(color: Colors.white)),
                      backgroundColor: Colors.blueGrey[700],
                      onPressed: () {
                        _usernameController.text = user;
                        _handleLogin();
                      },
                    );
                  }).toList(),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }

  @override
  void dispose() {
    _usernameController.dispose();
    _usernameFocus.dispose();
    _drawerController.dispose();
    super.dispose();
  }
}