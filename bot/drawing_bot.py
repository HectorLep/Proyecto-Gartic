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
    def __init__(self, image_path, canvas_region, mode='palette', exact_color_coords=None, brush_coords=None):
        self.image_path = image_path
        self.canvas_region = canvas_region
        self.mode = mode
        self.exact_color_coords = exact_color_coords
        self.brush_coords = brush_coords
        self.pause_event = threading.Event()
        self.cancel_event = threading.Event()
        # --- AÑADE ESTE BLOQUE DE LÓGICA AQUÍ ---
        # Asignar un paso de dibujo por defecto según el modo
        if self.mode == 'exact':
            # El modo preciso usa el paso más pequeño para máximo detalle
            self.brush_step = 2
            print("🖌️ Modo Preciso seleccionado. Usando paso de dibujo fino (2px).")
        elif self.mode == 'palette':
            # El modo paleta usa un paso medio para balancear velocidad y calidad
            self.brush_step = 11
            print("🖌️ Modo Paleta seleccionado. Usando paso de dibujo medio (11px).")
        # Nota: El modo 'smart' define su propio brush_step dinámicamente, por lo que no necesita un valor aquí.
        # --- FIN DEL BLOQUE A AÑADIR ---
        # Cargar paleta de colores
        self.load_palette()
        

        # Configuración de pyautogui
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0
                
        # --- POR ESTE NUEVO DICCIONARIO ---
        self.available_colors = {
            '0,0,0': (0, 0, 0),                           # Negro
            '102,102,102': (102, 102, 102),               # Gris medio oscuro
            '0,80,205': (0, 80, 205),                     # Azul intenso
            '255,255,255': (255, 255, 255),               # Blanco
            '170,170,170': (170, 170, 170),               # Gris claro
            '38,201,255': (38, 201, 255),                 # Cian brillante
            '1,116,32': (1, 116, 32),                     # Verde oscuro
            '153,0,0': (153, 0, 0),                       # Rojo oscuro
            '150,65,18': (150, 65, 18),                   # Marrón rojizo
            '17,176,60': (17, 176, 60),                   # Verde brillante
            '255,0,19': (255, 0, 19),                     # Rojo brillante
            '255,120,41': (255, 120, 41),                 # Naranja fuerte
            '176,112,28': (176, 112, 28),                 # Marrón mostaza
            '153,0,78': (153, 0, 78),                     # Fucsia oscuro
            '203,90,87': (203, 90, 87),                   # Rojo salmón oscuro
            '255,193,38': (255, 193, 38),                 # Amarillo dorado
            '255,0,143': (255, 0, 143),                   # Rosa fuerte / Fucsia neón
            '254,175,168': (254, 175, 168)                # Rosa claro / Salmón claro
        }
                
    # AÑADE ESTA FUNCIÓN NUEVA
    def _choose_best_brush(self, layer):
        """Analiza una capa y elige el mejor pincel y paso de dibujo."""
        # Contamos los píxeles totales para tener una idea general
        total_pixels = np.sum(layer > 0)

        # Si son muy pocos píxeles, es un detalle pequeño, usamos el pincel más fino
        if total_pixels < 50:
            return "brush_5", 2 # Pincel 3px, paso 2

        # Analizamos el "grosor" promedio de las líneas en la capa
        line_thicknesses = []
        for row in layer:
            # Encontrar segmentos de píxeles en la fila
            segments = np.where(row > 0)[0]
            if len(segments) > 0:
                # Calcular la longitud de los segmentos contiguos
                jumps = np.diff(segments) > 1
                runs = np.split(segments, np.where(jumps)[0] + 1)
                for run in runs:
                    line_thicknesses.append(len(run))

        if not line_thicknesses:
            return "brush_5", 2 # Si no hay líneas, es detalle, pincel pequeño

        avg_thickness = np.mean(line_thicknesses)

        # Decidimos el pincel basado en el grosor promedio
        if avg_thickness > 18:
            return "brush_1", 18 # Pincel 23px, paso 18
        elif avg_thickness > 12:
            return "brush_2", 14 # Pincel 18px, paso 14
        elif avg_thickness > 8:
            return "brush_3", 11 # Pincel 14px, paso 11
        elif avg_thickness > 4:
            return "brush_4", 7  # Pincel 9px, paso 7
        else:
            return "brush_5", 2  # Pincel 3px, paso 2

    # REEMPLAZA TU FUNCIÓN draw_by_smart_mode ENTERA CON ESTA
    def draw_by_smart_mode(self, progress_callback=None):
        """Dibuja usando un pincel adecuado para cada capa de color."""
        try:
            progress_callback("Iniciando dibujo en MODO INTELIGENTE...")
            time.sleep(3)
            # Procesar imagen (igual que antes)
            if self.image_path.lower().endswith('.png'):
                pil_image = self._process_png_with_transparency(self.image_path)
            else:
                pil_image = Image.open(self.image_path).convert('RGB')
            pil_image = self._enhance_image_quality(pil_image)
            canvas_w, canvas_h = self.canvas_region[2], self.canvas_region[3]
            pil_image.thumbnail((canvas_w, canvas_h), Image.Resampling.LANCZOS)
            image_array = np.array(pil_image)
            height, width = image_array.shape[:2]

            drawn_mask = np.zeros((height, width), dtype=np.uint8)

            progress_callback("Analizando colores...")
            exact_colors = self._extract_dominant_colors(image_array, num_colors=50, map_to_palette=False)
            if not exact_colors: raise Exception("No se pudieron detectar colores.")

            total_colors = len(exact_colors)
            for i, color in enumerate(exact_colors):
                if self._check_controls() == "cancel": break
                if color[0] > 240 and color[1] > 240 and color[2] > 240: continue

                # Crear la capa de color
                layer = np.zeros((height, width), dtype=np.uint8)
                for y in range(height):
                    for x in range(width):
                        pixel_color = tuple(image_array[y, x])
                        distance = self._color_distance(pixel_color, color)
                        if distance < 25:
                            layer[y, x] = 255

                # Quitar píxeles ya dibujados
                layer[drawn_mask == 255] = 0

                if np.any(layer):
                    # --- EL CAMBIO CLAVE ---
                    # 1. El bot elige el mejor pincel y paso para esta capa específica
                    brush_key, self.brush_step = self._choose_best_brush(layer)

                    progress_callback(f"Color {i+1}/{total_colors}: Usando pincel {brush_key} ({self.brush_step}px step)")

                    # 2. Selecciona el color y el pincel elegido
                    if not self._select_exact_color(tuple(map(int, color))): continue

                    # 3. Dibuja la capa con el paso optimizado
                    self._draw_layer_optimized(layer, "exact_mode")

                    # 4. Actualiza la máscara de memoria
                    drawn_mask[layer > 0] = 255

            progress_callback("¡Dibujo inteligente completado!")
        except Exception as e:
            progress_callback(f"Error en modo inteligente: {str(e)}")
            
    # AÑADE ESTA NUEVA FUNCIÓN
    def _select_brush(self, brush_key):
        """Selecciona un pincel haciendo clic en su coordenada calibrada."""
        if not self.brush_coords or brush_key not in self.brush_coords:
            print(f"⚠️ Coordenadas para '{brush_key}' no calibradas. Usando pincel actual.")
            return False

        try:
            coord = self.brush_coords[brush_key]
            pyautogui.click(coord)
            time.sleep(0.1)
            return True
        except Exception as e:
            print(f"Error seleccionando el pincel {brush_key}: {e}")
            return False

    # AÑADE ESTA FUNCIÓN NUEVA
    def _select_exact_color(self, rgb_tuple):
        """Selecciona un color personalizado introduciendo sus valores RGB."""
        r, g, b = rgb_tuple
        coords = self.exact_color_coords

        try:
            # 1. Abrir el selector de color
            pyautogui.click(coords['palette_button'])
            time.sleep(0.1)

            # 2. Introducir valor R
            pyautogui.click(coords['r_field'])
            time.sleep(0.05)
            pyautogui.hotkey('ctrl', 'a')
            pyautogui.press('backspace')
            pyautogui.typewrite(str(r), interval=0.01)

            # 3. Introducir valor G
            pyautogui.click(coords['g_field'])
            time.sleep(0.05)
            pyautogui.hotkey('ctrl', 'a')
            pyautogui.press('backspace')
            pyautogui.typewrite(str(g), interval=0.01)

            # 4. Introducir valor B
            pyautogui.click(coords['b_field'])
            time.sleep(0.05)
            pyautogui.hotkey('ctrl', 'a')
            pyautogui.press('backspace')
            pyautogui.typewrite(str(b), interval=0.01)

            # 5. Cerrar el selector (haciendo clic de nuevo en el botón)
            pyautogui.click(coords['palette_button'])
            time.sleep(0.15)
            return True
        except Exception as e:
            print(f"Error seleccionando color exacto {rgb_tuple}: {e}")
            return False
        
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
        
    # REEMPLAZA TU FUNCIÓN _extract_dominant_colors ENTERA CON ESTA:
    def _extract_dominant_colors(self, image_array, num_colors=10, map_to_palette=True):
        try:
            # 1. Preparar los datos de los píxeles
            if hasattr(self, 'transparency_mask') and self.transparency_mask is not None:
                # Caso para imágenes con transparencia
                mask_resized = cv2.resize(self.transparency_mask.astype(np.uint8), 
                                        (image_array.shape[1], image_array.shape[0]))
                visible_pixels = image_array[mask_resized > 0]
                
                if len(visible_pixels) == 0:
                    print("⚠️ No hay píxeles visibles en la imagen")
                    return []
                
                data = visible_pixels.reshape((-1, 3))
            else:
                # Caso para imágenes sin transparencia
                data = image_array.reshape((-1, 3))

            # 2. Analizar colores (ESTA PARTE AHORA ESTÁ BIEN INDENTADA)
            non_white_mask = ~((data[:, 0] > 240) & (data[:, 1] > 240) & (data[:, 2] > 240))
            if np.any(non_white_mask):
                data = data[non_white_mask]
            
            if len(data) == 0: return []

            actual_clusters = min(num_colors, len(np.unique(data, axis=0)))
            if actual_clusters < 2: return []
            
            kmeans = KMeans(n_clusters=actual_clusters, random_state=42, n_init=10)
            kmeans.fit(data)
            
            colors = kmeans.cluster_centers_.astype(int)
            unique_labels, counts = np.unique(kmeans.labels_, return_counts=True)
            color_freq = list(zip(colors, counts))
            color_freq.sort(key=lambda x: x[1], reverse=True)

            # 3. Devolver el resultado según el modo
            if not map_to_palette:
                exact_colors = [tuple(c) for c, freq in color_freq]
                print(f"🎨 Extraídos {len(exact_colors)} colores exactos.")
                return exact_colors

            mapped_colors = []
            for color, freq in color_freq:
                closest = self._find_closest_palette_color(tuple(color))
                if closest and closest not in [c[0] for c in mapped_colors]:
                    mapped_colors.append((closest, tuple(color), freq))
            
            return mapped_colors

        except Exception as e:
            print(f"Error extrayendo colores dominantes: {e}")
            return []
        
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
        
    # REEMPLAZA LA FUNCIÓN ENTERA
    def _draw_layer_optimized(self, layer, color_key, progress_callback=None):
        """Dibuja una capa con algoritmo optimizado, saltando líneas según el pincel."""
        if color_key != "exact_mode":
            if not self._select_color(color_key):
                return

        canvas_x_start, canvas_y_start = self.canvas_region[0], self.canvas_region[1]
        height, width = layer.shape

        # Bucle 'while' para permitir saltos de 'y'
        y = 0
        while y < height:
            if self._check_controls() == "cancel":
                return

            x = 0
            while x < width:
                # Buscar inicio de línea
                if layer[y, x] == 255:
                    start_x = x
                    # Buscar final de línea
                    while x < width and layer[y, x] == 255:
                        x += 1
                    end_x = x - 1

                    # Dibujar la línea
                    screen_start_x = canvas_x_start + start_x
                    screen_start_y = canvas_y_start + y
                    screen_end_x = canvas_x_start + end_x

                    pyautogui.moveTo(screen_start_x, screen_start_y, duration=0)
                    time.sleep(0.02)
                    pyautogui.mouseDown()
                    if end_x > start_x:
                        pyautogui.moveTo(screen_end_x, screen_start_y, duration=0.01)
                    pyautogui.mouseUp()
                    time.sleep(0.03)
                else:
                    x += 1

            # ¡EL GRAN CAMBIO! Saltamos píxeles en el eje Y
            y += self.brush_step
                
    def draw_by_layers(self, progress_callback=None):
        """Método principal que elige el flujo de dibujo según el modo."""
        if self.mode == 'smart': # <-- AÑADE ESTE ELIF
            self.draw_by_smart_mode(progress_callback)
        elif self.mode == 'exact':
            self.draw_by_exact_colors(progress_callback)
        else: # modo 'palette'
            self.draw_by_palette_colors(progress_callback)

    # EN drawing_bot.py, ASEGÚRATE DE TENER ESTA FUNCIÓN
    def draw_by_palette_colors(self, progress_callback=None):
        """Método de dibujo por paleta (tu función original renombrada)."""
        #
        # AQUÍ VA TODO EL CÓDIGO de tu función de dibujo original
        # que usaba la paleta de 18 colores para crear y dibujar las capas.
        #
        try:
            progress_callback("Iniciando dibujo en MODO PALETA...")
            time.sleep(3)
            # ...el resto de tu código de dibujo por paleta...
            
        except Exception as e:
            error_msg = f"Error durante el dibujo por paleta: {str(e)}"
            print(f"❌ {error_msg}")
            progress_callback(error_msg)

    # REEMPLAZA TU FUNCIÓN draw_by_exact_colors ENTERA CON ESTA:
    def draw_by_exact_colors(self, progress_callback=None):
        """Dibuja usando colores exactos de forma eficiente, evitando repintar."""
        try:
            progress_callback("Iniciando dibujo en MODO PRECISO...")
            time.sleep(3)

            # Paso 1: Procesar imagen (sin cambios)
            if self.image_path.lower().endswith('.png'):
                pil_image = self._process_png_with_transparency(self.image_path)
            else:
                pil_image = Image.open(self.image_path).convert('RGB')
            pil_image = self._enhance_image_quality(pil_image)
            canvas_w, canvas_h = self.canvas_region[2], self.canvas_region[3]
            pil_image.thumbnail((canvas_w, canvas_h), Image.Resampling.LANCZOS)
            image_array = np.array(pil_image)
            height, width = image_array.shape[:2]

            # --- INICIO DE CAMBIOS IMPORTANTES ---

            # NUEVO: Crear un "mapa" para recordar los píxeles ya dibujados.
            drawn_mask = np.zeros((height, width), dtype=np.uint8)

            # --- FIN DE CAMBIOS IMPORTANTES ---

            # Paso 2: Extraer colores exactos (sin cambios)
            progress_callback("Analizando paleta de colores exacta...")
            exact_colors = self._extract_dominant_colors(image_array, num_colors=50, map_to_palette=False)
            if not exact_colors:
                raise Exception("No se pudieron detectar colores en la imagen.")

            # Paso 3: Dibujar cada capa de color, pero solo en áreas no pintadas
            total_colors = len(exact_colors)
            for i, color in enumerate(exact_colors):
                if self._check_controls() == "cancel": break
                
                # El blanco puro suele ser el fondo, lo omitimos para acelerar
                if color[0] > 240 and color[1] > 240 and color[2] > 240:
                    continue

                progress_callback(f"Procesando color {i+1}/{total_colors}: RGB{color}")

                # Crear la capa de forma flexible (sin cambios)
                layer = np.zeros((height, width), dtype=np.uint8)
                color_threshold = 25
                for y in range(height):
                    for x in range(width):
                        pixel_color = tuple(image_array[y, x])
                        distance = self._color_distance(pixel_color, color)
                        if distance < color_threshold:
                            layer[y, x] = 255
                
                # --- INICIO DE CAMBIOS IMPORTANTES ---

                # NUEVO: Antes de dibujar, eliminamos de la capa actual los píxeles
                # que ya han sido pintados por un color anterior.
                layer[drawn_mask == 255] = 0

                # Si todavía quedan píxeles por dibujar en esta capa...
                if np.any(layer):
                    progress_callback(f"Dibujando color {i+1}/{total_colors}: RGB{color}")
                    
                    if not self._select_exact_color(color):
                        print(f"⚠️ Omitiendo color {color} por error en la selección.")
                        continue

                    self._draw_layer_optimized(layer, color_key="exact_mode", progress_callback=progress_callback)

                    # NUEVO: Actualizamos nuestro mapa de memoria, marcando las nuevas
                    # áreas como ya dibujadas.
                    drawn_mask[layer == 255] = 255

                # --- FIN DE CAMBIOS IMPORTANTES ---
                
            progress_callback("¡Dibujo de alta precisión completado!")

        except Exception as e:
            error_msg = f"Error durante el dibujo preciso: {str(e)}"
            print(f"❌ {error_msg}")
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