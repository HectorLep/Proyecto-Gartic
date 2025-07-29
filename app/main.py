import sys
import os
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import Qt

# Añadir el directorio actual al path para imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def check_dependencies():
    """Verifica que todas las dependencias estén instaladas"""
    required_packages = [
        'PyQt6', 'pyautogui', 'PIL', 'numpy', 'cv2', 
        'sklearn', 'pynput', 'colorsys'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            if package == 'PIL':
                import PIL
            elif package == 'cv2':
                import cv2
            elif package == 'sklearn':
                import sklearn
            elif package == 'colorsys':
                import colorsys
            else:
                __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print("❌ Faltan las siguientes dependencias:")
        for pkg in missing_packages:
            print(f"   - {pkg}")
        print("\n📦 Instala las dependencias con:")
        print("pip install PyQt6 pyautogui Pillow numpy opencv-python scikit-learn pynput")
        return False
    
    return True

def setup_directories():
    """Crea los directorios necesarios"""
    directories = ['assets', 'bot', 'app']
    
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"📁 Directorio creado: {directory}")

def run():
    """Función principal de la aplicación"""
    # Verificar dependencias
    if not check_dependencies():
        input("\nPresiona Enter para salir...")
        sys.exit(1)
    
    # Configurar directorios
    setup_directories()
    
    # Crear archivos __init__.py si no existen
    init_files = ['bot/__init__.py', 'app/__init__.py']
    for init_file in init_files:
        if not os.path.exists(init_file):
            with open(init_file, 'w') as f:
                f.write('# Init file\n')
    
    try:
        # Importar después de verificar dependencias
        from app.main_window import MainWindow
        
        # Configurar aplicación
        app = QApplication(sys.argv)
        app.setApplicationName("Gartic Phone Bot")
        app.setApplicationVersion("2.0")
        
        # Configurar estilo
        app.setStyle('Fusion')
        
        # Crear y mostrar ventana principal
        window = MainWindow()
        window.show()
        
        print("🚀 Aplicación iniciada correctamente")
        print("💡 Consejos:")
        print("   1. Primero calibra la paleta de colores")
        print("   2. Configura el área de dibujo")
        print("   3. ¡Disfruta dibujando!")
        
        # Ejecutar aplicación
        sys.exit(app.exec())
        
    except ImportError as e:
        print(f"❌ Error importando módulos: {e}")
        print("Asegúrate de que todos los archivos estén en su lugar correcto.")
        input("Presiona Enter para salir...")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        input("Presiona Enter para salir...")
        sys.exit(1)

if __name__ == "__main__":
    run()