#!/bin/bash
echo "🚀 Iniciando build en Render..."

# Precargar datos estáticos
echo "📥 Precargando dataset de anime..."
python src/services/preload_dataset.py

# Verificar que el dataset se creó
if [ -f "data/merged_anime.csv" ]; then
    echo "✅ Dataset base creado exitosamente"
    echo "📊 Tamaño del archivo: $(du -h data/merged_anime.csv | cut -f1)"
else
    echo "⚠️ Dataset base no se creó, se generará en el primer request"
fi

echo "✅ Build completado"