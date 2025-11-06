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
  bool _isDragging = false;

  final Map<String, Map<String, String>> _fallback = {
    'es': {
      'clear_data': 'Borrar datos',
      'data_cleared': 'Datos borrados correctamente',
    },
    'en': {
      'clear_data': 'Clear data',
      'data_cleared': 'Data cleared successfully',
    },
  };

  @override
  void initState() {
    super.initState();
    _loadLanguage();
    _loadSavedUsers();
    _drawerController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 280),
    );
  }

  Future<void> _loadLanguage() async {
    final prefs = await SharedPreferences.getInstance();
    final savedLang = prefs.getString('language') ?? 'es';
    final jsonStr = await rootBundle.loadString('assets/localization.json');
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

    final jsonStr = await rootBundle.loadString('assets/localization.json');
    final jsonData = json.decode(jsonStr);
    setState(() {
      _language = newLang;
      _localizedTexts = jsonData;
    });
  }

  String tr(String key) {
    return _localizedTexts[_language]?[key] ??
        _localizedTexts['es']?[key] ??
        key;
  }

  String trOrFallback(String key) {
    final fromJson = _localizedTexts[_language]?[key];
    if (fromJson != null) return fromJson;
    if (_fallback[_language]?[key] != null) return _fallback[_language]![key]!;
    return _localizedTexts['es']?[key] ?? _fallback['es']?[key] ?? key;
  }

  Future<void> _loadSavedUsers() async {
    final prefs = await SharedPreferences.getInstance();
    setState(() {
      _savedUsers = prefs.getStringList('saved_users') ?? [];
      _isUserSaved = _savedUsers.isNotEmpty;
    });
    ApiService.clearCache();
  }

  Future<void> _saveUser(String username) async {
    final prefs = await SharedPreferences.getInstance();
    List<String> currentUsers = prefs.getStringList('saved_users') ?? [];

    if (_isUserSaved) {
      currentUsers.remove(username);
      currentUsers.insert(0, username);
      if (currentUsers.length > _maxSuggestions) {
        currentUsers = currentUsers.sublist(0, _maxSuggestions);
      }
      await prefs.setStringList('saved_users', currentUsers);
    } else {
      await prefs.remove('saved_users');
      currentUsers.clear();
    }

    setState(() {
      _savedUsers = currentUsers;
    });
  }

  Future<void> _clearAllData() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.clear();
    await ApiService.clearCache();

    setState(() {
      _savedUsers = [];
      _isUserSaved = false;
    });

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(trOrFallback('data_cleared'))),
    );
  }

  void _validateAndNavigate() async {
    final username = _usernameController.text.trim();
    if (username.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(tr('login_screen_error_empty'))),
      );
      return;
    }

    _usernameFocus.unfocus();

    showDialog(
      context: context,
      barrierDismissible: false,
      barrierColor: Colors.black54,
      builder: (BuildContext dialogContext) => WillPopScope(
        onWillPop: () async => false,
        child: Dialog(
          backgroundColor: Colors.white,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
          ),
          child: Padding(
            padding: const EdgeInsets.all(20.0),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                const CircularProgressIndicator(),
                const SizedBox(width: 20),
                Flexible(
                  child: Text(
                    tr('login_screen_loading'),
                    style: const TextStyle(fontSize: 16),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );

    try {
      final cachedData = await ApiService.loadDataFromCache(username);
      if (cachedData != null) {
        await _saveUser(username);
        _navigateToRecommendations(username, cachedData);
        return;
      }

      final result = await PythonRunner.runTrainModel(username: username);
      await _saveUser(username);
      _navigateToRecommendations(username, result);
    } catch (e) {
      if (Navigator.of(context).canPop()) Navigator.of(context).pop();
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('${tr('login_screen_error_api')} $e')),
      );
    }
  }

  void _navigateToRecommendations(String username, Map<String, dynamic> data) {
    if (Navigator.of(context).canPop()) Navigator.of(context).pop();
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (context) => AnimeRecommendationsScreen(
          recommendations: data['recommendations'] as List<dynamic>,
          statistics: data['statistics'] as Map<String, dynamic>,
          tr: tr,
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final keyboardVisible = MediaQuery.of(context).viewInsets.bottom > 0;
    final screenWidth = MediaQuery.of(context).size.width;
    final drawerWidth = screenWidth * 0.5;
    const double edgeDragWidth = 200.0; // zona táctil para deslizar

    return Scaffold(
      backgroundColor: Colors.transparent,
      body: Stack(
        children: [
          // Fondo con color base + imagen
          Positioned.fill(
            child: Container(
              color: const Color(0xFF3E497A),
              child: AnimatedOpacity(
                opacity: keyboardVisible ? 0.7 : 1.0,
                duration: const Duration(milliseconds: 300),
                child: Image.asset(
                  'assets/background_img.png',
                  fit: BoxFit.cover,
                ),
              ),
            ),
          ),

          // Contenido principal
          SafeArea(
            child: Padding(
              padding:
                  const EdgeInsets.symmetric(horizontal: 32.0, vertical: 16),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  // Parte superior
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const SizedBox(height: 20),
                      Text(
                        tr('login_screen_user_label'),
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 24,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      const SizedBox(height: 20),
                      TextField(
                        controller: _usernameController,
                        focusNode: _usernameFocus,
                        textAlign: TextAlign.start,
                        style:
                            const TextStyle(color: Color(0xFF3E497A), fontSize: 18),
                        decoration: InputDecoration(
                          hintText: tr('login_screen_placeholder'),
                          hintStyle:
                              TextStyle(color: const Color(0xFF3E497A).withOpacity(0.6)),
                          filled: true,
                          fillColor: Colors.white,
                          border: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(10),
                            borderSide: BorderSide.none,
                          ),
                          contentPadding:
                              const EdgeInsets.symmetric(vertical: 15, horizontal: 15),
                        ),
                        onSubmitted: (_) => _validateAndNavigate(),
                      ),
                      const SizedBox(height: 10),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.start,
                        children: [
                          Checkbox(
                            value: _isUserSaved,
                            onChanged: (bool? newValue) {
                              setState(() {
                                _isUserSaved = newValue ?? false;
                              });
                            },
                            activeColor: Colors.white,
                            checkColor: const Color(0xFF3E497A),
                          ),
                          Text(
                            tr('login_screen_save_user'),
                            style: const TextStyle(color: Colors.white, fontSize: 16),
                          ),
                        ],
                      ),
                    ],
                  ),

                  // Parte inferior: botón
                  Padding(
                    padding: const EdgeInsets.only(bottom: 40),
                    child: ElevatedButton(
                      onPressed: _validateAndNavigate,
                      style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.white.withOpacity(0.9),
                        padding:
                            const EdgeInsets.symmetric(horizontal: 60, vertical: 16),
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
                  ),
                ],
              ),
            ),
          ),

          // Zona táctil invisible en el borde izquierdo (solo para deslizar)
          Positioned(
            left: 0,
            top: 0,
            bottom: 0,
            width: edgeDragWidth,
            child: GestureDetector(
              behavior: HitTestBehavior.translucent,
              onHorizontalDragStart: (details) {
                setState(() {
                  _isDragging = true;
                });
              },
              onHorizontalDragUpdate: (details) {
                final delta = details.delta.dx;
                if (delta > 0) { // Solo si desliza hacia la derecha
                  final newValue =
                      (_drawerController.value + delta / drawerWidth).clamp(0.0, 1.0);
                  _drawerController.value = newValue;
                }
              },
              onHorizontalDragEnd: (details) {
                setState(() {
                  _isDragging = false;
                });
                if (_drawerController.value > 0.3) {
                  _drawerController.forward();
                } else {
                  _drawerController.reverse();
                }
              },
            ),
          ),

          // Fondo semitransparente al abrir el menú
          AnimatedBuilder(
            animation: _drawerController,
            builder: (_, __) {
              final t = _drawerController.value;
              if (t <= 0.0) return const SizedBox.shrink();
              return Positioned.fill(
                child: GestureDetector(
                  onTap: () => _drawerController.reverse(),
                  child: Container(
                    color: Colors.black.withOpacity(0.4 * t),
                  ),
                ),
              );
            },
          ),

          // Drawer manual (mitad de pantalla, responsive text)
          AnimatedBuilder(
            animation: _drawerController,
            builder: (_, __) {
              final value = _drawerController.value;
              if (value <= 0.0) return const SizedBox.shrink();
              
              return Positioned(
                left: -drawerWidth + drawerWidth * value,
                top: 0,
                bottom: 0,
                width: drawerWidth,
                child: GestureDetector(
                  onHorizontalDragUpdate: (details) {
                    final delta = details.delta.dx;
                    if (delta < 0) { // Solo si desliza hacia la izquierda
                      final newValue =
                          (_drawerController.value + delta / drawerWidth).clamp(0.0, 1.0);
                      _drawerController.value = newValue;
                    }
                  },
                  onHorizontalDragEnd: (details) {
                    if (_drawerController.value < 0.7) {
                      _drawerController.reverse();
                    } else {
                      _drawerController.forward();
                    }
                  },
                  child: Container(
                    color: const Color(0xFF3E497A),
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 60),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Padding(
                          padding: const EdgeInsets.only(left: 10.0),
                          child: Text(
                            tr('app_title'),
                            style: const TextStyle(
                                color: Colors.white,
                                fontSize: 22,
                                fontWeight: FontWeight.bold),
                          ),
                        ),
                        const Divider(color: Colors.white54, height: 40),
                        
                        // 🗑️ Borrar datos
                        ListTile(
                          horizontalTitleGap: 0,
                          leading: const Padding(
                            padding: EdgeInsets.only(left: 4.0),
                            child: Icon(Icons.delete, color: Colors.white),
                          ),
                          title: FittedBox(
                            fit: BoxFit.scaleDown,
                            alignment: Alignment.centerLeft,
                            child: Text(
                              trOrFallback('clear_data'),
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
                            await _clearAllData();
                          },
                        ),

                        // 🌐 Cambiar idioma
                        ListTile(
                          horizontalTitleGap: 0,
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
              );
            },
          ),
        ],
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