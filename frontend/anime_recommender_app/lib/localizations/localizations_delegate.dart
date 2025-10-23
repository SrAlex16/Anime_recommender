
import 'package:flutter/material.dart';
import 'localizations.dart'; // Importa la clase AppLocalizations

class AppLocalizationsDelegate extends LocalizationsDelegate<AppLocalizations> {
  // Constante para el delegado
  const AppLocalizationsDelegate();

  // 1. Determina si el Locale dado es soportado por esta aplicación
  @override
  bool isSupported(Locale locale) {
    // Definir los códigos de idioma que soporta tu app
    return ['en', 'es'].contains(locale.languageCode);
  }

  // 2. Carga una instancia de AppLocalizations para el Locale dado
  @override
  Future<AppLocalizations> load(Locale locale) async {
    // Crea la instancia de la clase de localización
    AppLocalizations localizations = AppLocalizations(locale);
    
    // Carga el archivo JSON
    await localizations.load(); 
    
    return localizations;
  }

  // 3. Determina si el delegado debe ser recargado
  // Generalmente false, ya que las traducciones no cambian en tiempo de ejecución
  @override
  bool shouldReload(AppLocalizationsDelegate old) => false;
}