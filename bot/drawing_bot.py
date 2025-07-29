import pyautogui
import time
import json
import threading
import os
from PIL import Image, ImageEnhance
import numpy as np
import cv2
from sklearn.cluster import KMeans
import colorsys

class DrawingBot:
    def __init__(self, image_path, canvas_region):
        self.image_path = image_path
        self.canvas_region = canvas_region
        self.pause_event = threading.Event()
        self.cancel_event = threading.Event()
        
        # Cargar paleta de colores
        self.load_palette()
        
        # Configuración de pyautogui
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0
        
        # Colores disponibles en RGB para el mapeo inteligente
        self.available_colors = {
            '0,0,0': (0, 0, 0),           # Negro
            '89,89,89': (89, 89, 89),     # Gris oscuro
            '0,85,255': (0, 85, 255),     # Azul
            '255,255,255': (255, 255, 255), # Blanco
            '193,193,193': (193, 193, 193), # Gris claro
            '0,171,255': (0, 171, 255),   # Azul claro
            '0,128,0': (0, 128, 0),       # Verde oscuro
            '128,0,0': (128, 0, 0),       # Rojo oscuro
            '101,67,33': (101, 67, 33),   # Marrón oscuro
            '0,204,0': (0, 204, 0),       # Verde claro
            '239,19,11': (239, 19, 11),   # Rojo
            '255,113,0': (255, 113, 0),   # Naranja
            '210,129,63': (210, 129, 63), # Marrón medio
            '145,0,255': (145, 0, 255),   # Morado
            '255,175,175': (255, 175, 175), # Rosa claro
            '255,228,0': (255, 228, 0),   # Amarillo
            '255,0,255': (255, 0, 255),   # Rosa brillante
            '255,192,203': (255, 192, 203)  # Rosa pálido
        }
    
    def load_palette(self):
        """Carga la paleta de colores calibrada"""
        try:
            with open('assets/palette.json', 'r') as f:
                self.palette_data = json.load(f)['colors']
        except FileNotFoundError:
            raise Exception("Archivo de paleta no encontrado. Por favor calibra la paleta primero.")
        except Exception as e:
            raise Exception(f"Error cargando paleta: {str(e)}")
    
    def _check_controls(self, mouse_down=False):
        """Verifica controles de pausa y cancelación"""
        if self.cancel_event.is_set():
            if mouse_down:
                pyautogui.mouseUp()
            return "cancel"
        
        if self.pause_event.is_set():
            if mouse_down:
                pyautogui.mouseUp()
            print("⏸️ Dibujo pausado. Presiona F9 para reanudar.")
            self.pause_event.wait()
            print("▶️ Reanudando dibujo...")
            if mouse_down:
                pyautogui.mouseDown()
        
        return "continue"
    
    def _process_png_with_transparency(self, image_path):
        """Procesa imágenes PNG manteniendo la transparencia (SIN fondo gris)"""
        try:
            # Abrir imagen con PIL
            pil_image = Image.open(image_path)
            
            # Si tiene canal alpha (transparencia)
            if pil_image.mode in ('RGBA', 'LA'):
                print("🔍 Detectada imagen con transparencia - manteniendo áreas transparentes")
                
                # NO crear fondo - mantener la transparencia
                # Convertir RGBA a RGB pero manteniendo info de transparencia
                if pil_image.mode == 'RGBA':
                    # Crear una versión RGB donde lo transparente queda como "vacío"
                    rgb_image = Image.new('RGB', pil_image.size, (255, 255, 255))  # Fondo blanco temporal
                    
                    # Extraer canal alpha
                    alpha = pil_image.split()[-1]
                    
                    # Combinar solo donde hay contenido visible (alpha > umbral)
                    rgb_data = pil_image.convert('RGB')
                    
                    # Crear máscara de transparencia mejorada
                    alpha_array = np.array(alpha)
                    rgb_array = np.array(rgb_data)
                    
                    # Marcar píxeles transparentes/semi-transparentes como "sin dibujar"
                    # Solo consideraremos píxeles con alpha > 200 como sólidos
                    solid_mask = alpha_array > 200
                    
                    # Crear imagen final manteniendo solo píxeles sólidos
                    final_image = Image.new('RGB', pil_image.size, (255, 255, 255))
                    final_array = np.array(final_image)
                    
                    # Solo copiar píxeles que no son transparentes
                    final_array[solid_mask] = rgb_array[solid_mask]
                    
                    # Crear máscara de áreas a dibujar
                    self.transparency_mask = solid_mask
                    
                    return Image.fromarray(final_array)
                else:  # LA (grayscale con alpha)
                    alpha = pil_image.split()[-1]
                    alpha_array = np.array(alpha)
                    self.transparency_mask = alpha_array > 200
                    
                    rgb_image = pil_image.convert('RGB')
                    return rgb_image
            else:
                # Si no tiene transparencia, usar toda la imagen
                print("🔍 Imagen sin transparencia - procesando completa")
                self.transparency_mask = None
                return pil_image.convert('RGB')
                
        except Exception as e:
            print(f"Error procesando PNG: {e}")
            return None
    
    def _enhance_image_quality(self, pil_image):
        """Mejora la calidad de la imagen para mejor reconocimiento de colores"""
        try:
            # Aumentar contraste ligeramente
            enhancer = ImageEnhance.Contrast(pil_image)
            pil_image = enhancer.enhance(1.3)  # Más contraste para mejor detección
            
            # Aumentar saturación para colores más vivos
            enhancer = ImageEnhance.Color(pil_image)
            pil_image = enhancer.enhance(1.2)  # Más saturación
            
            # Aumentar nitidez
            enhancer = ImageEnhance.Sharpness(pil_image)
            pil_image = enhancer.enhance(1.2)
            
            return pil_image
        except Exception as e:
            print(f"Error mejorando imagen: {e}")
            return pil_image
    
    def _color_distance(self, color1, color2):
        """Calcula la distancia entre dos colores usando fórmula más precisa"""
        # Usar distancia euclidiana ponderada (más precisa para percepción humana)
        r1, g1, b1 = color1
        r2, g2, b2 = color2
        
        # Pesos basados en percepción visual humana
        weight_r = 0.3
        weight_g = 0.59
        weight_b = 0.11
        
        return np.sqrt(weight_r * (r1 - r2)**2 + weight_g * (g1 - g2)**2 + weight_b * (b1 - b2)**2)
    
    def _find_closest_palette_color(self, target_color):
        """Encuentra el color más cercano en la paleta disponible"""
        min_distance = float('inf')
        closest_color = None
        
        for color_key, color_rgb in self.available_colors.items():
            distance = self._color_distance(target_color, color_rgb)
            if distance < min_distance:
                min_distance = distance
                closest_color = color_key
        
        return closest_color
    
    def _extract_dominant_colors(self, image_array, num_colors=10):
        """Extrae los colores dominantes de la imagen usando K-means mejorado"""
        try:
            # Si hay máscara de transparencia, usar solo píxeles visibles
            if hasattr(self, 'transparency_mask') and self.transparency_mask is not None:
                # Filtrar solo píxeles que deben dibujarse
                mask_resized = cv2.resize(self.transparency_mask.astype(np.uint8), 
                                        (image_array.shape[1], image_array.shape[0]))
                visible_pixels = image_array[mask_resized > 0]
                
                if len(visible_pixels) == 0:
                    print("⚠️ No hay píxeles visibles en la imagen")
                    return []
                
                data = visible_pixels.reshape((-1, 3))
            else:
                # Usar toda la imagen
                data = image_array.reshape((-1, 3))
            
            # Filtrar píxeles blancos puros (fondo)
            non_white_mask = ~((data[:, 0] > 240) & (data[:, 1] > 240) & (data[:, 2] > 240))
            if np.any(non_white_mask):
                data = data[non_white_mask]
            
            if len(data) == 0:
                print("⚠️ Solo píxeles blancos detectados")
                return []
            
            # Aplicar K-means con más clusters para mejor detección
            actual_clusters = min(num_colors, len(np.unique(data, axis=0)))
            if actual_clusters < 2:
                print("⚠️ Muy pocos colores únicos detectados")
                return []
            
            kmeans = KMeans(n_clusters=actual_clusters, random_state=42, n_init=10)
            kmeans.fit(data)
            
            # Obtener colores centrales y sus frecuencias
            colors = kmeans.cluster_centers_.astype(int)
            labels = kmeans.labels_
            
            # Calcular frecuencia de cada color
            unique_labels, counts = np.unique(labels, return_counts=True)
            color_freq = list(zip(colors, counts))
            
            # Ordenar por frecuencia (más común primero)
            color_freq.sort(key=lambda x: x[1], reverse=True)
            
            # Mapear a colores de paleta disponibles
            mapped_colors = []
            for color, freq in color_freq:
                closest = self._find_closest_palette_color(tuple(color))
                if closest and closest not in [c[0] for c in mapped_colors]:
                    mapped_colors.append((closest, tuple(color), freq))
                    print(f"🎨 Color detectado: {self._get_color_name(closest)} (frecuencia: {freq})")
            
            return mapped_colors
        
        except Exception as e:
            print(f"Error extrayendo colores dominantes: {e}")
            # Fallback más conservador
            return [
                ('0,0,0', (0, 0, 0), 1000),       # Negro
                ('239,19,11', (239, 19, 11), 800), # Rojo
                ('0,85,255', (0, 85, 255), 600),  # Azul
            ]
    
    def _create_color_layers(self, image_array, color_palette):
        """Crea capas para cada color en la paleta"""
        layers = {}
        height, width = image_array.shape[:2]
        
        # Aplicar máscara de transparencia si existe
        drawing_mask = None
        if hasattr(self, 'transparency_mask') and self.transparency_mask is not None:
            drawing_mask = cv2.resize(self.transparency_mask.astype(np.uint8), 
                                    (width, height))
        
        for color_key, original_color, freq in color_palette:
            # Crear máscara para este color
            layer = np.zeros((height, width), dtype=np.uint8)
            
            # Umbral de distancia más estricto para mejor precisión
            color_threshold = 30  # Reducido para mayor precisión
            
            # Para cada pixel, verificar si pertenece a este color
            for y in range(height):
                for x in range(width):
                    # Verificar si el píxel debe dibujarse (no transparente)
                    if drawing_mask is not None and drawing_mask[y, x] == 0:
                        continue
                    
                    pixel_color = tuple(image_array[y, x])
                    
                    # Calcular distancia directa al color original detectado
                    distance = self._color_distance(pixel_color, original_color)
                    
                    if distance < color_threshold:
                        layer[y, x] = 255
            
            # Solo agregar capas que tienen contenido
            if np.any(layer == 255):
                layers[color_key] = layer
                pixel_count = np.sum(layer == 255)
                print(f"📝 Capa {self._get_color_name(color_key)}: {pixel_count} píxeles")
            else:
                print(f"⚠️ Capa {self._get_color_name(color_key)}: vacía, omitiendo")
        
        return layers
    
    def _select_color(self, color_key):
        """Selecciona un color en la paleta de Gartic Phone"""
        try:
            if color_key in self.palette_data:
                coord = self.palette_data[color_key]
                pyautogui.click(coord[0], coord[1])
                time.sleep(0.15)  # Pausa ligeramente mayor para asegurar selección
                return True
            else:
                print(f"⚠️ Color {color_key} no encontrado en paleta calibrada")
                return False
        except Exception as e:
            print(f"Error seleccionando color {color_key}: {e}")
            return False
    
    def _draw_layer_optimized(self, layer, color_key, progress_callback=None):
        """Dibuja una capa con algoritmo optimizado de líneas"""
        if not self._select_color(color_key):
            return
        
        canvas_x_start, canvas_y_start = self.canvas_region[0], self.canvas_region[1]
        height, width = layer.shape
        
        lines_drawn = 0
        total_pixels = np.sum(layer == 255)
        pixels_drawn = 0
        
        print(f"🖌️ Iniciando dibujo de {self._get_color_name(color_key)} ({total_pixels} píxeles)")
        
        # Dibujar líneas horizontales
        for y in range(height):
            if self._check_controls() == "cancel":
                return
            
            x = 0
            while x < width:
                # Buscar inicio de línea
                while x < width and layer[y, x] != 255:
                    x += 1
                
                if x < width:
                    start_x = x
                    # Buscar final de línea
                    while x < width and layer[y, x] == 255:
                        x += 1
                    end_x = x - 1
                    
                    # Dibujar línea solo si es suficientemente larga (mínimo 1 píxel)
                    if end_x >= start_x:
                        screen_start_x = canvas_x_start + start_x
                        screen_start_y = canvas_y_start + y
                        screen_end_x = canvas_x_start + end_x
                        screen_end_y = canvas_y_start + y
                                                
                        # Bloque de código DEFINITIVO

                        # Mover al punto de inicio
                        pyautogui.moveTo(screen_start_x, screen_start_y, duration=0)

                        # AÑADE ESTA PAUSA: Le da tiempo al sistema para registrar la nueva posición del cursor
                        time.sleep(0.02)

                        # Presionar el botón del mouse
                        pyautogui.mouseDown()

                        # Si es una línea, mover al final.
                        if end_x > start_x:
                            pyautogui.moveTo(screen_end_x, screen_end_y, duration=0.01)

                        # Soltar el botón del mouse
                        pyautogui.mouseUp()

                        # AUMENTA LA PAUSA FINAL: Dale un poco más de tiempo para procesar el "mouseUp"
                        time.sleep(0.03)
                        
                        lines_drawn += 1
                        pixels_drawn += (end_x - start_x + 1)
                        
                        # Actualizar progreso cada 20 líneas
                        if lines_drawn % 20 == 0 and progress_callback:
                            progress = min(pixels_drawn / max(total_pixels, 1) * 100, 100)
                            progress_callback(f"Dibujando {self._get_color_name(color_key)}: {progress:.1f}%")
        
        print(f"✅ Completado {self._get_color_name(color_key)}: {lines_drawn} líneas, {pixels_drawn} píxeles")
    
    def draw_by_layers(self, progress_callback=None):
        """Método principal de dibujo por capas inteligentes"""
        try:
            if progress_callback:
                progress_callback("Iniciando dibujo inteligente...")
            
            print("🎨 Iniciando modo de dibujo INTELIGENTE por capas...")
            print("⌨️  Atajos: F9 (Pausar/Reanudar), F10 (Cancelar)")
            
            time.sleep(3)  # Tiempo para prepararse
            
            # Paso 1: Procesar imagen
            if progress_callback:
                progress_callback("Procesando imagen...")
            
            # Manejar PNG con transparencia correctamente (SIN fondo gris)
            if self.image_path.lower().endswith('.png'):
                pil_image = self._process_png_with_transparency(self.image_path)
            else:
                pil_image = Image.open(self.image_path).convert('RGB')
                self.transparency_mask = None  # No hay transparencia
            
            if pil_image is None:
                raise Exception("No se pudo procesar la imagen")
            
            # Mejorar calidad de imagen
            pil_image = self._enhance_image_quality(pil_image)
            
            # Redimensionar para ajustar al canvas
            canvas_w, canvas_h = self.canvas_region[2], self.canvas_region[3]
            original_size = pil_image.size
            pil_image.thumbnail((canvas_w, canvas_h), Image.Resampling.LANCZOS)
            
            print(f"📏 Imagen redimensionada de {original_size} a {pil_image.size}")
            
            # Convertir a array numpy
            image_array = np.array(pil_image)
            
            if progress_callback:
                progress_callback("Analizando colores de la imagen...")
            
            # Paso 2: Extraer colores dominantes
            dominant_colors = self._extract_dominant_colors(image_array, num_colors=12)
            
            if not dominant_colors:
                raise Exception("No se pudieron detectar colores en la imagen")
            
            print(f"🎨 Colores detectados para dibujo: {len(dominant_colors)}")
            
            # Paso 3: Crear capas de colores
            if progress_callback:
                progress_callback("Creando capas de colores...")
            
            color_layers = self._create_color_layers(image_array, dominant_colors)
            
            if not color_layers:
                raise Exception("No se pudieron crear capas de colores válidas")
            
            # Paso 4: Dibujar cada capa (ordenar por frecuencia - colores más comunes primero)
            sorted_colors = [(k, v) for k, v in color_layers.items()]
            total_colors = len(sorted_colors)
            
            for i, (color_key, layer) in enumerate(sorted_colors):
                if self._check_controls() == "cancel":
                    break
                
                color_name = self._get_color_name(color_key)
                print(f"🖌️  Dibujando capa {i+1}/{total_colors}: {color_name}")
                
                if progress_callback:
                    progress_callback(f"Capa {i+1}/{total_colors}: {color_name}")
                
                # Dibujar la capa
                self._draw_layer_optimized(layer, color_key, progress_callback)
                
                # Pequeña pausa entre capas
                time.sleep(0.3)
            
            if not self.cancel_event.is_set():
                if progress_callback:
                    progress_callback("¡Dibujo completado exitosamente!")
                print("✅ ¡Dibujo completado exitosamente!")
            else:
                if progress_callback:
                    progress_callback("Dibujo cancelado por el usuario")
                print("❌ Dibujo cancelado por el usuario.")
        
        except Exception as e:
            error_msg = f"Error durante el dibujo: {str(e)}"
            print(f"❌ {error_msg}")
            if progress_callback:
                progress_callback(error_msg)
    
    def _get_color_name(self, color_key):
        """Obtiene el nombre amigable del color"""
        color_names = {
            '0,0,0': 'Negro',
            '89,89,89': 'Gris oscuro', 
            '0,85,255': 'Azul',
            '255,255,255': 'Blanco',
            '193,193,193': 'Gris claro',
            '0,171,255': 'Azul claro',
            '0,128,0': 'Verde oscuro',
            '128,0,0': 'Rojo oscuro',
            '101,67,33': 'Marrón oscuro',
            '0,204,0': 'Verde claro',
            '239,19,11': 'Rojo',
            '255,113,0': 'Naranja',
            '210,129,63': 'Marrón medio',
            '145,0,255': 'Morado',
            '255,175,175': 'Rosa claro',
            '255,228,0': 'Amarillo',
            '255,0,255': 'Rosa brillante',
            '255,192,203': 'Rosa pálido'
        }
        return color_names.get(color_key, f'Color {color_key}')
    
    def pause_or_resume(self):
        """Pausa o reanuda el dibujo"""
        if self.pause_event.is_set():
            self.pause_event.clear()
        else:
            self.pause_event.set()
    
    def cancel(self):
        """Cancela el dibujo"""
        self.cancel_event.set()
        if self.pause_event.is_set():
            self.pause_event.clear()  # Liberar pausa para permitir cancelación