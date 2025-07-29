# 🎨 Gartic Phone Bot - Versión Mejorada

Un bot inteligente para dibujar automáticamente en Gartic Phone con soporte completo para colores y manejo mejorado de imágenes PNG.

## 🚀 Características Principales

- **Calibración Automática de Colores**: Interfaz intuitiva para calibrar la paleta de 18 colores
- **Manejo Inteligente de PNG**: Procesa correctamente imágenes PNG con transparencia
- **Dibujo por Capas**: Algoritmo optimizado que dibuja por capas de colores
- **Controles en Tiempo Real**: Pausa (F9) y cancela (F10) el dibujo cuando quieras
- **Interfaz Moderna**: UI con pestañas para fácil configuración
- **Detección Automática de Colores**: Usa K-means para encontrar los colores dominantes

## 📦 Instalación

1. **Clonar o descargar** el proyecto
2. **Instalar dependencias**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Ejecutar la aplicación**:
   ```bash
   python main.py
   ```

## 🎯 Cómo Usar

### Paso 1: Calibrar la Paleta de Colores
1. Ve a la pestaña "🎯 Calibrar Colores"
2. Abre Gartic Phone en tu navegador
3. Ve a la pantalla de dibujo donde aparece la paleta
4. Haz clic en "Iniciar Calibración" 
5. El cursor se moverá automáticamente - haz clic en cada color cuando se te pida
6. Guarda la configuración

### Paso 2: Configurar el Área de Dibujo
1. Ve a la pestaña "📐 Configurar Canvas"
2. Ajusta las coordenadas X, Y de la esquina superior izquierda del área de dibujo
3. Configura el ancho y alto del área
4. Usa "Probar Área" para verificar que la selección sea correcta
5. Guarda la configuración

### Paso 3: Dibujar
1. Ve a la pestaña "🎨 Dibujar"
2. Carga una imagen (PNG, JPG, JPEG soportados)
3. Haz clic en "🚀 ¡Iniciar Dibujo!"
4. El bot comenzará a dibujar automáticamente

## ⌨️ Atajos de Teclado

- **F9**: Pausar/Reanudar el dibujo
- **F10**: Cancelar el dibujo

## 🎨 Colores Soportados

El bot reconoce y usa los 18 colores estándar de Gartic Phone:

1. Negro
2. Gris oscuro  
3. Azul
4. Blanco
5. Gris claro
6. Azul claro
7. Verde oscuro
8. Rojo oscuro
9. Marrón oscuro
10. Verde claro
11. Rojo
12. Naranja
13. Marrón medio
14. Morado
15. Rosa claro
16. Amarillo
17. Rosa brillante
18. Rosa pálido

## 🔧 Resolución de Problemas

### El bot no encuentra los colores
- Asegúrate de haber calibrado la paleta correctamente
- Verifica que Gartic Phone esté visible en pantalla
- Recalibra si cambias la resolución o zoom del navegador

### Las imágenes PNG salen con fondo negro
- La nueva versión maneja automáticamente la transparencia
- Si persiste el problema, convierte la imagen a JPG primero

### El dibujo no se ve bien
- Usa imágenes con colores claros y definidos
- Evita imágenes muy complejas o con muchos gradientes
- Las imágenes tipo cartoon o con colores planos funcionan mejor

### Error al iniciar
- Verifica que todas las dependencias estén instaladas
- Ejecuta: `pip install -r requirements.txt`
- Asegúrate de usar Python 3.8 o superior

## 📁 Estructura del Proyecto

```
gartic-bot/
├── main.py                 # Archivo principal
├── requirements.txt        # Dependencias
├── README.md              # Este archivo
├── app/
│   ├── __init__.py
│   └── main_window.py     # Interfaz principal
├── bot/
│   ├── __init__.py
│   └── drawing_bot.py     # Lógica del bot
└── assets/
    ├── palette.json       # Paleta calibrada (se genera)
    └── canvas_config.json # Configuración del canvas (se genera)
```

## 🐛 Reportar Problemas

Si encuentras algún error o tienes sugerencias:

1. Describe el problema detalladamente
2. Incluye el mensaje de error (si lo hay)
3. Menciona tu sistema operativo y versión de Python
4. Adjunta una captura de pantalla si es relevante

## 📝 Notas Importantes

- **Uso Responsable**: Este bot es para uso educativo y entretenimiento
- **Rendimiento**: El tiempo de dibujo depende de la complejidad de la imagen
- **Compatibilidad**: Probado en Windows 10/11, macOS y Linux
- **Resolución**: Funciona mejor en resoluciones 1920x1080 o superiores

## 🎉 ¡Disfruta Dibujando!

¡Esperamos que disfrutes usando este bot! Si te gusta el proyecto, no dudes en compartirlo y dar feedback.
