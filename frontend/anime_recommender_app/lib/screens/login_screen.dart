// lib/screens/login_screen.dart
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'anime_recommendations_screen.dart';
import '../services/python_runner.dart';
import '../services/api_service.dart'; // ✅ Importar ApiService para la lógica de caché

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final TextEditingController _usernameController = TextEditingController();
  final FocusNode _usernameFocus = FocusNode();

  bool _isUserSaved = false;
  List<String> _savedUsers = [];
  Map<String, dynamic> _localizedTexts = {};
  String _language = 'es';

  static const int _maxSuggestions = 5;

  @override
  void initState() {
    super.initState();
    _loadLanguage();
    _loadSavedUsers();
  }

  Future<void> _loadLanguage() async {
    final prefs = await SharedPreferences.getInstance();
    final savedLang = prefs.getString('language') ?? 'es';
    final jsonStr = await rootBundle.loadString('assets/texts_localization.json');
    final jsonData = json.decode(jsonStr);
    setState(() {
      _language = savedLang;
      _localizedTexts = jsonData;
    });
  }

  Future<void> _toggleLanguage() async {
    final prefs = await SharedPreferences.getInstance();
    final newLang = _language == 'es' ? 'en' : 'es';
    await prefs.setString('language', newLang);
    setState(() {
      _language = newLang;
      // Recargar textos para el nuevo idioma
      _loadLanguage(); 
    });
  }

  String tr(String key) {
    if (_localizedTexts.isEmpty) return key;
    return _localizedTexts[_language]?[key] ?? key;
  }

  Future<void> _loadSavedUsers() async {
    final prefs = await SharedPreferences.getInstance();
    setState(() {
      _savedUsers = prefs.getStringList('savedUsernames') ?? [];
      if (_usernameController.text.isEmpty && _savedUsers.isNotEmpty) {
        _usernameController.text = _savedUsers.first;
      }
      // Inicializar _isUserSaved si hay texto
      _isUserSaved = _usernameController.text.isNotEmpty;
    });
  }

  Future<void> _saveUsername(String username) async {
    if (username.isEmpty) return;
    final prefs = await SharedPreferences.getInstance();
    _savedUsers.remove(username);
    _savedUsers.insert(0, username);
    if (_savedUsers.length > _maxSuggestions) {
      _savedUsers = _savedUsers.sublist(0, _maxSuggestions);
    }
    await prefs.setStringList('savedUsernames', _savedUsers);
  }

  Future<void> _clearData() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('savedUsernames');
    // ✅ TRADUCIDO
    await ApiService.clearCache(); // Asegurarse de limpiar la caché del API
    
    setState(() {
      _savedUsers.clear();
      _usernameController.clear();
      _isUserSaved = false;
    });
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(tr('sidebar_clear_confirmation'))), // ✅ Traducido
    );
  }

  void _showLoadingDialog() {
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) => AlertDialog(
        title: Text(tr('recommendations_loading_title')), // ✅ Traducido
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(tr('loading_message_running_engine')), // ✅ Traducido
            const SizedBox(height: 20),
            const CircularProgressIndicator(),
            const SizedBox(height: 20),
            Text(
              // ✅ Combinación de mensajes traducidos
              '${tr('recommendations_loading_message_info')}\n${tr('recommendations_loading_message_tip')}',
              textAlign: TextAlign.center,
              style: const TextStyle(fontSize: 12),
            ),
          ],
        ),
      ),
    );
  }

  void _showErrorDialog(String error) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(tr('error_dialog_title')), // ✅ Traducido
        content: SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(tr('error_message_general')), // ✅ Traducido
              const SizedBox(height: 16),
              Text(tr('error_solutions_title')), // ✅ Traducido
              const SizedBox(height: 8),
              Text(tr('error_solution_python')), // ✅ Traducido
              Text(tr('error_solution_dependencies')), // ✅ Traducido
              const Text('  pandas, numpy, scikit-learn, requests'), // Dependencias sin traducir
              Text(tr('error_solution_internet')), // ✅ Traducido
              const SizedBox(height: 16),
              Text(
                tr('error_technical_title'), // ✅ Traducido
                style: const TextStyle(fontWeight: FontWeight.bold),
              ),
              Text(
                error.length > 200 ? '${error.substring(0, 200)}...' : error,
                style: const TextStyle(fontSize: 12, color: Colors.red),
              ),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: Text(tr('common_ok')), // ✅ Traducido
          ),
        ],
      ),
    );
  }

  // 🔄 MÉTODO MODIFICADO: Implementa la lógica de caché y la llamada a la API
  void _validateAndNavigate() async {
    final username = _usernameController.text.trim();

    if (username.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        content: Text(tr('login_error_empty_user')),
        backgroundColor: Colors.red,
      ));
      return;
    }

    Map<String, dynamic>? resultData;
    bool loadedFromCache = false;

    try {
      // 1. INTENTAR CARGAR DATOS DESDE LA CACHÉ
      resultData = await ApiService.loadDataFromCache(username);

      if (resultData != null) {
        loadedFromCache = true;
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(tr('cache_loaded_message'))), // ✅ Traducido
        );
      } 
      
      // 2. SI NO HAY CACHÉ (O ES NULL), LLAMAR A LA API
      if (resultData == null || resultData!['status'] != 'success') {
        
        // Mostrar diálogo de carga antes de la llamada a la API
        _showLoadingDialog(); 
        
        // Llamada a la API (implementada en PythonRunner que usa ApiService)
        final apiResult = await PythonRunner.runTrainModel(username: username);
        
        // Cerrar el diálogo de carga al recibir respuesta
        if (Navigator.of(context, rootNavigator: true).canPop()) {
              Navigator.of(context, rootNavigator: true).pop();
        }
        
        // Mapear el resultado de la API
        resultData = {
          'recommendations': apiResult['recommendations'],
          'statistics': apiResult['statistics'],
          'status': 'success', 
        };
      }
      
      // 3. GUARDAR NOMBRE DE USUARIO (si está marcado)
      if (_isUserSaved) {
        await _saveUsername(username);
      }
      
      // 4. NAVEGAR, asegurando que resultData no es null
      if (resultData != null && resultData['recommendations'] is List && resultData['statistics'] is Map) {
          Navigator.of(context).push(
            MaterialPageRoute(
              builder: (context) => AnimeRecommendationsScreen(
                recommendations: resultData!['recommendations'] as List<dynamic>,
                statistics: resultData!['statistics'] as Map<String, dynamic>,
                tr: tr, // ✅ CRUCIAL: Pasamos la función de traducción
              ),
            ),
          );
      } else if (!loadedFromCache) {
          // Si la API devuelve datos, pero con formato incorrecto
          throw Exception('Error: Los datos de recomendaciones o estadísticas tienen un formato incorrecto.');
      }
      
    } on Exception catch (e) {
      // Asegurar el cierre del diálogo de carga en caso de error
      if (Navigator.of(context, rootNavigator: true).canPop()) {
          Navigator.of(context, rootNavigator: true).pop();
      }
      
      print('❌ Error: $e');
      _showErrorDialog(e.toString());
    }
  }

  @override
  Widget build(BuildContext context) {
    // ... (El Drawer y el cuerpo ya usan tr() correctamente)
    return Scaffold(
      drawerEdgeDragWidth: MediaQuery.of(context).size.width,
      drawer: Drawer(
        backgroundColor: const Color(0xFF3E497A),
        child: SafeArea(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Padding(
                padding:
                    const EdgeInsets.symmetric(horizontal: 24.0, vertical: 32.0),
                child: Text(
                  tr('sidebar_title'),
                  style: const TextStyle(
                      color: Colors.white,
                      fontSize: 24,
                      fontWeight: FontWeight.bold),
                ),
              ),
              const Divider(color: Colors.white24),
              ListTile(
                leading: const Icon(Icons.delete, color: Colors.white70),
                title: Text(tr('sidebar_clear_data'),
                    style: const TextStyle(color: Colors.white70)),
                onTap: _clearData,
              ),
              ListTile(
                leading: const Icon(Icons.language, color: Colors.white70),
                title: Text(tr('language_switch'),
                    style: const TextStyle(color: Colors.white70)),
                onTap: _toggleLanguage,
              ),
            ],
          ),
        ),
      ),
      body: Stack(
        fit: StackFit.expand,
        children: [
          Image.asset(
            'assets/background_img.png',
            fit: BoxFit.cover,
          ),
          Container(color: Colors.black.withOpacity(0.3)),
          SafeArea(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 32.0),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const SizedBox(height: 30),
                      Text(
                        tr('login_screen_title'),
                        style: const TextStyle(
                          color: Colors.white70,
                          fontSize: 22,
                          fontWeight: FontWeight.normal,
                        ),
                      ),
                      const SizedBox(height: 12),

                      _isUserSaved
                          ? Autocomplete<String>(
                              optionsBuilder: (TextEditingValue textEditingValue) {
                                if (textEditingValue.text.isEmpty) {
                                  return const Iterable<String>.empty();
                                }
                                return _savedUsers.where((user) => user
                                    .toLowerCase()
                                    .contains(textEditingValue.text.toLowerCase()));
                              },
                              fieldViewBuilder: (context, controller, focusNode, onFieldSubmitted) {
                                controller.text = _usernameController.text;
                                return TextField(
                                  controller: controller,
                                  focusNode: focusNode,
                                  decoration: InputDecoration(
                                    filled: true,
                                    fillColor: Colors.white,
                                    hintText: tr('login_screen_hint'),
                                    border: OutlineInputBorder(
                                      borderRadius: BorderRadius.circular(12),
                                      borderSide: BorderSide.none,
                                    ),
                                    contentPadding: const EdgeInsets.symmetric(
                                        horizontal: 16, vertical: 14),
                                  ),
                                  onSubmitted: (_) => _validateAndNavigate(),
                                  onChanged: (value) {
                                    _usernameController.text = value;
                                    _usernameController.selection = controller.selection;
                                  },
                                );
                              },
                              onSelected: (String selection) {
                                _usernameController.text = selection;
                              },
                            )
                          : TextField(
                              controller: _usernameController,
                              focusNode: _usernameFocus,
                              decoration: InputDecoration(
                                filled: true,
                                fillColor: Colors.white,
                                hintText: tr('login_screen_hint'),
                                border: OutlineInputBorder(
                                  borderRadius: BorderRadius.circular(12),
                                  borderSide: BorderSide.none,
                                ),
                                contentPadding: const EdgeInsets.symmetric(
                                    horizontal: 16, vertical: 14),
                              ),
                              onSubmitted: (_) => _validateAndNavigate(),
                            ),

                      const SizedBox(height: 8),
                      Row(
                        children: [
                          Theme(
                            data: ThemeData(
                              checkboxTheme: CheckboxThemeData(
                                shape: RoundedRectangleBorder(
                                    borderRadius: BorderRadius.circular(4)),
                                side: const BorderSide(color: Colors.white, width: 2),
                                fillColor: MaterialStateProperty.resolveWith<Color>(
                                  (Set<MaterialState> states) {
                                    if (states.contains(MaterialState.selected)) {
                                      return Colors.white;
                                    }
                                    return Colors.transparent;
                                  },
                                ),
                              ),
                            ),
                            child: Checkbox(
                              value: _isUserSaved,
                              onChanged: (v) => setState(() {
                                _isUserSaved = v ?? false;
                              }),
                              checkColor: const Color(0xFF3E497A),
                            ),
                          ),
                          Text(
                            tr('login_screen_save_user'),
                            style: const TextStyle(
                                color: Colors.white70, fontSize: 16),
                          ),
                        ],
                      ),
                    ],
                  ),

                  Column(
                    children: [
                      Text(
                        tr('login_screen_note'),
                        textAlign: TextAlign.center,
                        style: const TextStyle(
                          color: Colors.white70,
                          fontSize: 15,
                          fontStyle: FontStyle.italic,
                        ),
                      ),
                      const SizedBox(height: 20),
                      ElevatedButton(
                        onPressed: _validateAndNavigate,
                        style: ElevatedButton.styleFrom(
                          backgroundColor: Colors.white.withOpacity(0.9),
                          padding: const EdgeInsets.symmetric(
                              horizontal: 45, vertical: 14),
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(30),
                          ),
                        ),
                        child: Text(
                          tr('login_screen_button'),
                          style: const TextStyle(
                            color: Color(0xFF3E497A),
                            fontSize: 18,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ),
                      const SizedBox(height: 30),
                    ],
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  @override
  void dispose() {
    _usernameController.dispose();
    _usernameFocus.dispose();
    super.dispose();
  }
}