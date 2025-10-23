import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

class AppLocalizations {
  final Locale locale;
  Map<String, String> _localizedStrings = {};

  AppLocalizations(this.locale);

  static AppLocalizations? of(BuildContext context) {
    return Localizations.of<AppLocalizations>(context, AppLocalizations);
  }

  Future<bool> load() async {
    try {
      // ✅ CORREGIDO: Nombre correcto del archivo
      String jsonString = await rootBundle.loadString('assets/texts_localization.json');
      Map<String, dynamic> jsonMap = json.decode(jsonString);

      // ✅ CORREGIDO: Obtener las traducciones para el idioma actual
      Map<String, dynamic> languageData = jsonMap[locale.languageCode] ?? jsonMap['es'];
      
      // ✅ Añadir claves por defecto si no existen
      languageData.putIfAbsent('sidebar_clear_data', () => locale.languageCode == 'es' ? 'Borrar datos' : 'Clear Data');
      languageData.putIfAbsent('sidebar_clear_confirmation', () => locale.languageCode == 'es' ? 'Datos de usuario borrados.' : 'User data cleared.');

      _localizedStrings = languageData.map((key, value) {
        return MapEntry(key, value.toString());
      });

      return true;
    } catch (e) {
      print('❌ Error cargando localizaciones: $e');
      return false;
    }
  }

  String translate(String key) {
    return _localizedStrings[key] ?? key;
  }
}