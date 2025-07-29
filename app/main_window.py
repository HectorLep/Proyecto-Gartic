import sys
import json
import os
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QFileDialog, QMessageBox, 
                             QProgressBar, QTabWidget, QScrollArea, QGridLayout,
                             QSpinBox, QGroupBox)
from PyQt6.QtCore import QThread, pyqtSignal, QObject, Qt
from PyQt6.QtGui import QPixmap, QFont
from bot.drawing_bot import DrawingBot
from pynput import keyboard, mouse # Importar mouse de pynput

# El listener de teclado no cambia
class KeyboardListener(QThread):
    pause_pressed = pyqtSignal()
    cancel_pressed = pyqtSignal()
    
    def run(self):
        def on_press(key):
            try:
                if key == keyboard.Key.f9: 
                    self.pause_pressed.emit()
                elif key == keyboard.Key.f10: 
                    self.cancel_pressed.emit()
            except:
                pass
        
        with keyboard.Listener(on_press=on_press) as listener:
            listener.join()

# Listener de mouse para la calibración
class MouseClickListener(QThread):
    mouse_clicked = pyqtSignal(int, int)

    def __init__(self):
        super().__init__()
        self.listener = None

    def run(self):
        def on_click(x, y, button, pressed):
            if pressed and button == mouse.Button.left:
                self.mouse_clicked.emit(x, y)
        
        self.listener = mouse.Listener(on_click=on_click)
        self.listener.start()
        self.listener.join()

    def stop(self):
        if self.listener:
            self.listener.stop()

# El worker para el dibujo no cambia
class Worker(QObject):
    finished = pyqtSignal()
    progress = pyqtSignal(str)
    
    def __init__(self, bot):
        super().__init__()
        self.bot = bot
    
    def run(self):
        try:
            self.bot.draw_by_layers(progress_callback=self.progress.emit)
            self.finished.emit()
        except Exception as e:
            self.progress.emit(f"Error: {str(e)}")
            self.finished.emit()

# Clase de calibración de color completamente reescrita
class ColorCalibrationWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.color_positions = {}
        self.current_color_index = 0
        self.is_calibrating = False
        self.mouse_listener = None
        
        self.colors = [
            ("Negro", "0,0,0"), ("Blanco", "255,255,255"), ("Gris claro", "193,193,193"),
            ("Gris oscuro", "89,89,89"), ("Rojo", "239,19,11"), ("Naranja", "255,113,0"),
            ("Amarillo", "255,228,0"), ("Verde claro", "0,204,0"), ("Azul claro", "0,171,255"),
            ("Azul", "0,85,255"), ("Morado", "145,0,255"), ("Rosa brillante", "255,0,255"),
            ("Marrón medio", "210,129,63"), ("Rosa claro", "255,175,175")
            # Añade más si es necesario
        ]
        
        self.setup_ui()
        self.load_existing_palette()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        title = QLabel("Calibración de Paleta de Colores")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignCenter)
        
        instructions = QLabel("1. Abre Gartic Phone en la pantalla de dibujo.\n"
                              "2. Haz clic en 'Iniciar/Detener Calibración'.\n"
                              "3. El programa esperará a que hagas clic en cada color.")
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
        
        self.toggle_calibration_btn = QPushButton("🎯 Iniciar Calibración")
        self.toggle_calibration_btn.setCheckable(True)
        self.toggle_calibration_btn.clicked.connect(self.toggle_calibration)
        
        self.save_palette_btn = QPushButton("💾 Guardar Paleta")
        self.save_palette_btn.clicked.connect(self.save_palette)
        self.save_palette_btn.setEnabled(False)
        
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.toggle_calibration_btn)
        button_layout.addWidget(self.save_palette_btn)
        layout.addLayout(button_layout)
        
        self.status_label = QLabel("Estado: Listo para calibrar")
        layout.addWidget(self.status_label, alignment=Qt.AlignmentFlag.AlignCenter)
        
        self.setup_color_display()
        layout.addWidget(self.color_scroll_area)
    
    def setup_color_display(self):
        self.color_scroll_area = QScrollArea()
        self.color_widget = QWidget()
        self.color_layout = QGridLayout(self.color_widget)
        
        self.color_labels = {}
        for i, (name, rgb) in enumerate(self.colors):
            row, col = i // 3, i % 3
            frame = QGroupBox(name)
            frame_layout = QVBoxLayout(frame)
            color_display = QLabel()
            color_display.setFixedSize(50, 30)
            color_display.setStyleSheet(f"background-color: rgb({rgb}); border: 1px solid black;")
            coord_label = QLabel("No calibrado")
            
            frame_layout.addWidget(color_display, alignment=Qt.AlignmentFlag.AlignCenter)
            frame_layout.addWidget(coord_label, alignment=Qt.AlignmentFlag.AlignCenter)
            self.color_labels[rgb] = coord_label
            self.color_layout.addWidget(frame, row, col)
            
        self.color_scroll_area.setWidget(self.color_widget)
        self.color_scroll_area.setWidgetResizable(True)
        self.color_scroll_area.setMaximumHeight(350)
    
    def load_existing_palette(self):
        if os.path.exists('assets/palette.json'):
            try:
                with open('assets/palette.json', 'r') as f:
                    data = json.load(f)
                    self.color_positions = data.get('colors', {})
                    self.update_color_display()
                    self.save_palette_btn.setEnabled(True)
            except json.JSONDecodeError:
                self.status_label.setText("Error: 'palette.json' está corrupto.")
            except Exception as e:
                self.status_label.setText(f"Error: {e}")

    def update_color_display(self):
        for rgb, label in self.color_labels.items():
            if rgb in self.color_positions:
                pos = self.color_positions[rgb]
                label.setText(f"({pos[0]}, {pos[1]})")
                label.setStyleSheet("color: green; font-weight: bold;")
            else:
                label.setText("No calibrado")
                label.setStyleSheet("color: red;")

    def toggle_calibration(self, checked):
        if checked:
            self.start_calibration()
        else:
            self.stop_calibration()

    def start_calibration(self):
        reply = QMessageBox.question(self, "Iniciar Calibración",
                                     "Asegúrate de que Gartic Phone esté visible.\n"
                                     "El programa capturará tu siguiente clic para cada color.\n"
                                     "¿Estás listo?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            self.is_calibrating = True
            self.toggle_calibration_btn.setText("🛑 Detener Calibración")
            self.current_color_index = 0
            
            # Iniciar el listener de clics
            self.mouse_listener = MouseClickListener()
            self.mouse_listener.mouse_clicked.connect(self.on_color_clicked)
            self.mouse_listener.start()
            
            self.prompt_next_color()
        else:
            self.toggle_calibration_btn.setChecked(False)

    def stop_calibration(self):
        self.is_calibrating = False
        self.toggle_calibration_btn.setText("🎯 Iniciar Calibración")
        self.status_label.setText("Calibración detenida por el usuario.")
        
        if self.mouse_listener:
            self.mouse_listener.stop()
            self.mouse_listener.quit()
            self.mouse_listener.wait()
            self.mouse_listener = None
        
        self.save_palette_btn.setEnabled(len(self.color_positions) > 0)

    def prompt_next_color(self):
        if not self.is_calibrating: return
        
        if self.current_color_index < len(self.colors):
            color_name, _ = self.colors[self.current_color_index]
            self.status_label.setText(f"➡️  Haz clic en el color: {color_name}")
        else:
            self.finish_calibration()

    def on_color_clicked(self, x, y):
        if not self.is_calibrating: return
        
        _, color_rgb = self.colors[self.current_color_index]
        self.color_positions[color_rgb] = [x, y]
        
        print(f"Calibrado {self.colors[self.current_color_index][0]} en ({x}, {y})")
        
        self.update_color_display()
        self.current_color_index += 1
        self.prompt_next_color()

    def finish_calibration(self):
        self.stop_calibration()
        self.toggle_calibration_btn.setChecked(False)
        self.status_label.setText("¡Calibración completada!")
        QMessageBox.information(self, "Calibración Completa", "Todos los colores han sido calibrados.\nNo olvides guardar la paleta.")

    def save_palette(self):
        os.makedirs('assets', exist_ok=True)
        palette_data = {
            "description": "Paleta de Gartic Phone calibrada",
            "colors": self.color_positions
        }
        with open('assets/palette.json', 'w') as f:
            json.dump(palette_data, f, indent=4)
        QMessageBox.information(self, "Guardado Exitoso", "La paleta ha sido guardada en 'assets/palette.json'.")


# El resto de MainWindow y otras clases no necesita cambios importantes.
# Solo asegúrate de que se integren bien.
# El resto de tu código para MainWindow y CanvasCalibrationWidget es excelente. Lo mantendremos.

class CanvasCalibrationWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        title = QLabel("Calibración del Área de Dibujo")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        instructions = QLabel(
            "Configura el área donde se dibujará:\n"
            "1. Ajusta las coordenadas X, Y de la esquina superior izquierda\n"
            "2. Ajusta el ancho y alto del área de dibujo\n"
            "3. Usa 'Probar Área' para verificar la selección"
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
        
        # Controles de coordenadas
        coords_group = QGroupBox("Coordenadas del Área de Dibujo")
        coords_layout = QGridLayout(coords_group)
        
        # X coordinate
        coords_layout.addWidget(QLabel("X (izquierda):"), 0, 0)
        self.x_spin = QSpinBox()
        self.x_spin.setRange(0, 4000)
        self.x_spin.setValue(650)
        coords_layout.addWidget(self.x_spin, 0, 1)
        
        # Y coordinate
        coords_layout.addWidget(QLabel("Y (arriba):"), 0, 2)
        self.y_spin = QSpinBox()
        self.y_spin.setRange(0, 2000)
        self.y_spin.setValue(400)
        coords_layout.addWidget(self.y_spin, 0, 3)
        
        # Width
        coords_layout.addWidget(QLabel("Ancho:"), 1, 0)
        self.width_spin = QSpinBox()
        self.width_spin.setRange(100, 4000)
        self.width_spin.setValue(600)
        coords_layout.addWidget(self.width_spin, 1, 1)
        
        # Height
        coords_layout.addWidget(QLabel("Alto:"), 1, 2)
        self.height_spin = QSpinBox()
        self.height_spin.setRange(100, 2000)
        self.height_spin.setValue(450)
        coords_layout.addWidget(self.height_spin, 1, 3)
        
        layout.addWidget(coords_group)
        
        # Botones
        button_layout = QHBoxLayout()
        
        test_btn = QPushButton("🎯 Probar Área")
        test_btn.clicked.connect(self.test_canvas_area)
        button_layout.addWidget(test_btn)
        
        save_btn = QPushButton("💾 Guardar Configuración")
        save_btn.clicked.connect(self.save_canvas_config)
        button_layout.addWidget(save_btn)
        
        layout.addLayout(button_layout)
        
        self.status_label = QLabel("Estado: Listo para configurar")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)
    
    def test_canvas_area(self):
        """Muestra visualmente el área seleccionada"""
        try:
            x, y = self.x_spin.value(), self.y_spin.value()
            w, h = self.width_spin.value(), self.height_spin.value()
            
            self.status_label.setText("Mostrando área de dibujo...")
            
            # Mover mouse para mostrar las esquinas
            pyautogui.moveTo(x, y, duration=0.5)  # Esquina superior izquierda
            QThread.msleep(500)
            pyautogui.moveTo(x + w, y, duration=0.5)  # Esquina superior derecha
            QThread.msleep(500)
            pyautogui.moveTo(x + w, y + h, duration=0.5)  # Esquina inferior derecha
            QThread.msleep(500)
            pyautogui.moveTo(x, y + h, duration=0.5)  # Esquina inferior izquierda
            QThread.msleep(500)
            pyautogui.moveTo(x, y, duration=0.5)  # Volver al inicio
            
            self.status_label.setText("¡Área mostrada! ¿Se ve correcta?")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error probando área: {str(e)}")
    
    def save_canvas_config(self):
        """Guarda la configuración del canvas"""
        try:
            config = {
                "canvas_region": [
                    self.x_spin.value(),
                    self.y_spin.value(),
                    self.width_spin.value(),
                    self.height_spin.value()
                ]
            }
            
            os.makedirs('assets', exist_ok=True)
            with open('assets/canvas_config.json', 'w') as f:
                json.dump(config, f, indent=2)
            
            self.status_label.setText("¡Configuración guardada!")
            QMessageBox.information(
                self,
                "Guardado Exitoso",
                "Configuración del área de dibujo guardada correctamente."
            )
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error guardando configuración: {str(e)}")
    
    def get_canvas_region(self):
        """Retorna la región del canvas configurada"""
        try:
            if os.path.exists('assets/canvas_config.json'):
                with open('assets/canvas_config.json', 'r') as f:
                    return json.load(f)['canvas_region']
        except:
            pass # Usar valores por defecto si no hay config
        return (self.x_spin.value(), self.y_spin.value(), 
                self.width_spin.value(), self.height_spin.value())


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gartic Phone Bot - Versión Mejorada")
        self.setGeometry(100, 100, 800, 600)
        
        self.image_path = None
        self.bot = None
        self.drawing_thread = None
        self.worker = None
        
        self.setup_ui()
        self.setup_keyboard_listener()
    
    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        self.tabs = QTabWidget()
        self.drawing_tab = self.create_drawing_tab()
        self.color_calibration_tab = ColorCalibrationWidget(self)
        self.canvas_calibration_tab = CanvasCalibrationWidget(self)
        
        self.tabs.addTab(self.drawing_tab, "🎨 Dibujar")
        self.tabs.addTab(self.color_calibration_tab, "🎯 Calibrar Colores")
        self.tabs.addTab(self.canvas_calibration_tab, "📐 Configurar Canvas")
        
        layout.addWidget(self.tabs)
    
    def create_drawing_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        title = QLabel("Bot de Dibujo para Gartic Phone")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignCenter)
        
        self.image_preview = QLabel("Sin imagen cargada")
        self.image_preview.setMinimumHeight(200)
        self.image_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_preview.setStyleSheet("border: 2px dashed #ccc; background-color: #f9f9f9;")
        layout.addWidget(self.image_preview)
        
        button_layout = QHBoxLayout()
        self.load_button = QPushButton("📁 Cargar Imagen")
        self.load_button.clicked.connect(self.load_image)
        button_layout.addWidget(self.load_button)
        
        self.draw_button = QPushButton("🚀 ¡Iniciar Dibujo!")
        self.draw_button.clicked.connect(self.start_drawing)
        self.draw_button.setEnabled(False)
        button_layout.addWidget(self.draw_button)
        
        layout.addLayout(button_layout)
        
        shortcuts_info = QLabel("<b>Atajos:</b> F9 (Pausar/Reanudar) | F10 (Cancelar)")
        shortcuts_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(shortcuts_info)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("Estado: Esperando imagen...")
        layout.addWidget(self.status_label, alignment=Qt.AlignmentFlag.AlignCenter)
        
        return widget
    
    def setup_keyboard_listener(self):
        self.key_listener = KeyboardListener()
        self.key_listener.pause_pressed.connect(self.toggle_pause)
        self.key_listener.cancel_pressed.connect(self.cancel_drawing)
        self.key_listener.start()
    
    def load_image(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Seleccionar Imagen", "", "Images (*.png *.jpg *.jpeg *.bmp)")
        
        if file_name:
            self.image_path = file_name
            try:
                pixmap = QPixmap(file_name)
                self.image_preview.setPixmap(pixmap.scaled(self.image_preview.size(), 
                                               Qt.AspectRatioMode.KeepAspectRatio, 
                                               Qt.TransformationMode.SmoothTransformation))
            except Exception as e:
                self.image_preview.setText(f"Error preview: {e}")
            
            self.status_label.setText(f"Cargado: {os.path.basename(file_name)}")
            self.draw_button.setEnabled(True)
    
    def start_drawing(self):
        if not self.image_path:
            QMessageBox.warning(self, "Error", "Primero debes cargar una imagen.")
            return
        
        if not os.path.exists('assets/palette.json'):
            QMessageBox.warning(self, "Paleta no calibrada", 
                                "Ve a la pestaña 'Calibrar Colores' y calibra la paleta primero.")
            return
        
        try:
            canvas_region = self.canvas_calibration_tab.get_canvas_region()
            self.bot = DrawingBot(self.image_path, canvas_region)
            
            self.drawing_thread = QThread()
            self.worker = Worker(self.bot)
            self.worker.moveToThread(self.drawing_thread)
            
            self.worker.finished.connect(self.drawing_thread.quit)
            self.worker.progress.connect(self.update_progress)
            self.drawing_thread.started.connect(self.worker.run)
            self.drawing_thread.finished.connect(self.drawing_finished)
            
            self.toggle_ui_state(is_drawing=True)
            self.progress_bar.setVisible(True)
            
            self.drawing_thread.start()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error iniciando dibujo: {str(e)}")
            self.toggle_ui_state(is_drawing=False)

    def update_progress(self, message):
        self.status_label.setText(f"Estado: {message}")
    
    def toggle_pause(self):
        if self.bot and self.drawing_thread and self.drawing_thread.isRunning():
            self.bot.pause_or_resume()
            self.status_label.setText("Estado: ⏸️ PAUSADO" if self.bot.pause_event.is_set() else "Estado: ▶️ Dibujando...")
    
    def cancel_drawing(self):
        if self.bot and self.drawing_thread and self.drawing_thread.isRunning():
            self.bot.cancel()
            self.status_label.setText("Estado: ❌ Cancelando...")
    
    def drawing_finished(self):
        self.status_label.setText("Estado: ✅ Finalizado")
        self.progress_bar.setVisible(False)
        self.toggle_ui_state(is_drawing=False)
        
        self.bot = None
        self.worker = None
        if self.drawing_thread:
            self.drawing_thread.deleteLater()
            self.drawing_thread = None
    
    def toggle_ui_state(self, is_drawing):
        self.draw_button.setEnabled(not is_drawing)
        self.load_button.setEnabled(not is_drawing)
        self.tabs.setTabEnabled(1, not is_drawing) # Bloquear calibración mientras dibuja
        self.tabs.setTabEnabled(2, not is_drawing)
        if is_drawing:
            self.status_label.setText("Estado: 🎨 Dibujando...")
    
    def closeEvent(self, event):
        if self.drawing_thread and self.drawing_thread.isRunning():
            self.cancel_drawing()
            self.drawing_thread.quit()
            self.drawing_thread.wait(2000)
        
        if hasattr(self, 'key_listener'):
            self.key_listener.terminate()
            self.key_listener.wait(500)
        
        event.accept()