# =============================================================================================
# APPLICAZIONE DI ACCESSO BIOMETRICO - Face Detection & Recording System con YOLO Object Detection
# =============================================================================================
import os
import sys
import json
import cv2
import time
import datetime
import geocoder
import logging
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication, QLabel, QPushButton, QVBoxLayout, QWidget,
    QHBoxLayout, QGroupBox, QColorDialog, QCheckBox, QSlider,
    QComboBox, QFileDialog, QMessageBox, QSizePolicy, QScrollArea, QLineEdit
)
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QImage, QPixmap, QColor, QMouseEvent
import numpy as np
import threading
import queue
import concurrent.futures
from ultralytics import YOLO
from settings import settings_manager, ThemeMode
from theme_engine import ThemeEngine

# =============================================================================================
# CONFIGURAZIONE LOGGING
# =============================================================================================
LOG_FILE = os.path.join("logs", "faceapp_logging.log")
Path("logs").mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    encoding='utf-8',
    filemode='a'
)
logger = logging.getLogger("FaceApp")

# =============================================================================================
# COSTANTI
# =============================================================================================
STATS_FILE = "stats.json"
KNOWN_OBJECTS_DIR = Path("known_objects")
KNOWN_OBJECTS_DIR.mkdir(exist_ok=True)

RECOGNITION_INTERVAL = 8           # ogni quanti frame tentare riconoscimento
MIN_GOOD_MATCHES = 15              # aumentato un po' perché usiamo frame intero
MATCH_DISTANCE_THRESHOLD = 65
MIN_SCORE = 0.28


def open_camera_with_fallback(index):
    """
    Try to open a camera with multiple backend fallbacks for better compatibility
    with PyInstaller-packaged executables.
    Returns tuple of (cap object or None, backend used or None).
    """
    import platform
    
    # Only apply fallback on Windows
    if platform.system() != 'Windows':
        cap = cv2.VideoCapture(index)
        if cap.isOpened():
            return cap, "default"
        return None, None
    
    # On Windows, try multiple backends in order of compatibility
    # CAP_DSHOW: DirectShow - most compatible, works without extra DLLs
    # CAP_MSMF: Microsoft Media Foundation - default but may have issues in packaged apps
    # CAP_VFW: Video for Windows - legacy but reliable
    
    backends = [
        (cv2.CAP_DSHOW, "DSHOW"),
        (cv2.CAP_MSMF, "MSMF"),
        (cv2.CAP_VFW, "VFW"),
    ]
    
    for backend, backend_name in backends:
        try:
            cap = cv2.VideoCapture(index, backend)
            if cap.isOpened():
                # Test if we can actually read a frame
                ret, frame = cap.read()
                if ret and frame is not None:
                    logger.info(f"Camera opened successfully with {backend_name} backend")
                    return cap, backend_name
                # Can open but can't read - release and try next
                cap.release()
        except Exception as e:
            logger.warning(f"Failed to open camera with {backend_name}: {e}")
            continue
    
    # Last resort - try without specifying backend
    try:
        cap = cv2.VideoCapture(index)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret and frame is not None:
                logger.info("Camera opened with default backend")
                return cap, "default"
            cap.release()
    except Exception as e:
        logger.warning(f"Failed to open camera with default backend: {e}")
    
    return None, None


def scan_webcams_with_fallback():
    """
    Scan for available webcams using multiple backends.
    Returns tuple of (indices, names).
    """
    indices = []
    names = []
    
    for i in range(10):
        try:
            cap, backend = open_camera_with_fallback(i)
            if cap is not None:
                indices.append(i)
                names.append(f"Webcam {i}")
                cap.release()
                logger.info(f"Found webcam {i}")
        except:
            continue
    
    return indices, names


# =============================================================================================
# SUBCLASS PER QLabel CLICCABILE
# =============================================================================================
class ClickableLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            parent = self.parent()
            if parent is not None and hasattr(parent, 'handle_object_click'):
                try:
                    parent.handle_object_click(event.pos())
                except Exception:
                    pass


# Lightweight frame grabber thread to reduce blocking on network streams
class FrameGrabber:
    def __init__(self, cap):
        self.cap = cap
        self._frame = None
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = None

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        while not self._stop.is_set():
            try:
                if self.cap is None:
                    time.sleep(0.05)
                    continue
                ret, frame = self.cap.read()
                if not ret:
                    time.sleep(0.02)
                    continue
                with self._lock:
                    self._frame = frame
            except Exception:
                time.sleep(0.05)

    def get_frame(self):
        with self._lock:
            if self._frame is None:
                return None
            return self._frame.copy()

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=0.5)

# =============================================================================================
# CLASSE PRINCIPALE
# =============================================================================================
class FaceApp(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("APPLICAZIONE DI ACCESSO BIOMETRICO + YOLO Object Detection")
        self.resize(1100, 600)
        self.setMinimumSize(900, 500)

        # Parametri base disegno volti
        self.rect_color = QColor(0, 255, 0)
        self.rect_thickness = 2
        self.show_coords = False
        self.show_fps = True
        self.zoom_factor = 1.0
        self.last_frame = None

        # Motion detection
        self.motion_enabled = True
        self.prev_gray = None
        self.motion_threshold = 5000
        self.motion_last_seen = time.time()
        self.motion_grace_seconds = 3
        self.motion_recording_active = False

        # Filtri e stato
        self.gray_filter = False
        self.recording = False
        self.video_writer = None
        self.record_start_time = None
        self.recording_start_time = None
        self.face_detection_counter = 0

        # Statistiche
        self.photo_count = 0
        self.video_count = 0
        self.last_photo = "Nessuna"
        self.last_video = "Nessuno"
        self.save_path = os.getcwd()
        self.load_stats()

        # Geolocalizzazione
        self.location = "Località sconosciuta"
        try:
            g = geocoder.ip("me")
            if g.city or g.country:
                self.location = f"{g.city or ''}, {g.country or ''}".strip(", ")
        except Exception:
            pass

        # Webcam - Use fallback mechanism for better compatibility
        logger.info("Inizializzazione webcam...")
        self.available_indices, self.available_names = scan_webcams_with_fallback()
        
        if not self.available_indices:
            logger.error("Nessuna webcam trovata")
            raise RuntimeError("Nessuna webcam trovata.")

        self.current_cam_index = self.available_indices[0]
        self.current_cam_name = self.available_names[0]
        
        # Try to open with fallback mechanism
        self.cap, self.current_backend = open_camera_with_fallback(self.current_cam_index)
        
        if self.cap is None or not self.cap.isOpened():
            logger.error("Impossibile aprire la webcam principale")
            raise RuntimeError("Impossibile aprire la webcam principale.")
        
        logger.info(f"Webcam aperta: {self.current_cam_name} con backend {self.current_backend}")

        # Start background frame grabber to smooth reads (helps network streams)
        self.frame_grabber = FrameGrabber(self.cap)
        self.frame_grabber.start()

        # Face detector (Haar Cascade)
        self.detector = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )

        # YOLO model
        self.yolo_model = YOLO("yolov8n.pt")  # Usa yolov8n.pt o scarica il modello desiderato (es. yolov11n.pt per versioni più recenti)

        # YOLO parameters
        self.yolo_enabled = True
        self.yolo_rect_color = QColor(0, 255, 0)  # green
        self.yolo_rect_thickness = 2
        self.yolo_results_cache = []  # Cache for YOLO results
        self.frame_counter = 0
        # Background executor for YOLO to avoid blocking UI
        self.yolo_executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        self.yolo_future = None
        self.yolo_freq = 6  # run YOLO every N frames

        # Interfaccia - Usa ClickableLabel invece di QLabel
        self.video_label = ClickableLabel(self)
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.cam_name_label = QLabel(f"Webcam attiva: {self.current_cam_name}", alignment=Qt.AlignCenter)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.running = False
        self.prev_time = time.time()
        self.fps = 0

        # Riconoscimento oggetti
        self.known_descriptors = {}  # nome → (descriptors, filename_senza_estensione)
        self.load_known_objects()
        self.current_recognition = None
        self.frame_counter = 0

        # Selezione oggetto
        self.selected_rect = None  # (x, y, w, h)

        # Layout sidebar
        settings_layout = QVBoxLayout()
        settings_layout.addWidget(self.create_webcam_group())
        settings_layout.addWidget(self.create_face_group())
        settings_layout.addWidget(self.create_yolo_group())
        settings_layout.addWidget(self.create_feedback_group())
        settings_layout.addWidget(self.create_savepath_group())
        settings_layout.addWidget(self.create_theme_group())
        # object recognition UI removed per user request
        settings_layout.addStretch()

        settings_container = QWidget()
        settings_container.setLayout(settings_layout)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(settings_container)
        self.scroll_area = scroll_area

        sidebar_layout = QVBoxLayout()
        # sidebar will contain only the scroll area (controls)
        sidebar_layout.addWidget(scroll_area, 1)

        sidebar_widget = QWidget()
        sidebar_widget.setLayout(sidebar_layout)
        sidebar_widget.setFixedWidth(420)
        self.sidebar_widget = sidebar_widget

        # Top controls (independent from sidebar): Start/Stop camera and settings toggle
        top_controls = QWidget()
        top_h = QHBoxLayout()
        top_h.setContentsMargins(0, 0, 0, 0)
        # Start/Stop camera button (independent)
        self.start_button = QPushButton("Start Camera")
        self.start_button.clicked.connect(self.toggle_camera)
        self.start_button.setStyleSheet("background-color: green; color: white;")
        self.start_button.setFixedWidth(120)
        top_h.addWidget(self.start_button)

        # Settings toggle button (gear / arrow)
        self.toggle_sidebar_button = QPushButton("⚙")
        self.toggle_sidebar_button.setToolTip("Mostra impostazioni")
        self.toggle_sidebar_button.setFixedWidth(40)
        self.toggle_sidebar_button.clicked.connect(self.toggle_sidebar)
        top_h.addWidget(self.toggle_sidebar_button)

        top_controls.setLayout(top_h)

        # Layout principale
        video_layout = QVBoxLayout()
        video_layout.addWidget(top_controls)
        video_layout.addWidget(self.cam_name_label)
        video_layout.addWidget(self.video_label)

        main_layout = QHBoxLayout(self)
        main_layout.addWidget(self.sidebar_widget, 0)
        main_layout.addLayout(video_layout, 1)
        # Start with sidebar hidden
        self.sidebar_widget.hide()
        # Ensure toggle button shows gear when hidden
        self.toggle_sidebar_button.setText("⚙")
        self.toggle_sidebar_button.setToolTip("Mostra impostazioni")

    # ========================================================================
    # METODI STATISTICHE
    # ========================================================================
    def load_stats(self):
        if not os.path.exists(STATS_FILE):
            return
        try:
            with open(STATS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.photo_count = data.get("photos", 0)
            self.video_count = data.get("videos", 0)
            self.last_photo = data.get("last_photo", "Nessuna")
            self.last_video = data.get("last_video", "Nessuno")
            self.save_path = data.get("save_path", os.getcwd())
        except Exception as e:
            logger.warning(f"Errore caricamento stats: {e}")

    def save_stats(self):
        data = {
            "photos": self.photo_count,
            "videos": self.video_count,
            "last_photo": self.last_photo,
            "last_video": self.last_video,
            "save_path": self.save_path,
        }
        try:
            with open(STATS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            logger.warning(f"Errore salvataggio stats: {e}")

    # ========================================================================
    # WEBCAM
    # ========================================================================
    def scan_webcams(self):
        """Legacy scan function - now uses fallback mechanism."""
        return scan_webcams_with_fallback()

    # ========================================================================
    # CREAZIONE PANNELLI
    # ========================================================================
    def create_webcam_group(self):
        group = QGroupBox("Webcam")
        layout = QVBoxLayout()
        self.cam_selector = QComboBox()
        for name in self.available_names:
            self.cam_selector.addItem(name)
        self.cam_selector.addItem("Camera Telefono")
        self.cam_selector.currentIndexChanged.connect(self.change_camera)
        layout.addWidget(self.cam_selector)

        self.phone_url_input = QLineEdit()
        self.phone_url_input.setPlaceholderText("Inserisci URL telefono (es. http://10.30.23.5:8080/video)")
        layout.addWidget(self.phone_url_input)
        # Start/Stop camera button is placed in the top controls (independent)
        self.record_button = QPushButton("Start Recording")
        self.record_button.clicked.connect(self.toggle_recording)
        self.record_button.setStyleSheet("background-color: #173c68; color: white;")
        layout.addWidget(self.record_button)
        group.setLayout(layout)
        group.setMaximumWidth(380)
        return group

    def create_face_group(self):
        group = QGroupBox("Rilevamento Volti")
        layout = QVBoxLayout()
        self.color_button = QPushButton("Colore rettangolo")
        self.color_button.clicked.connect(self.choose_color)
        layout.addWidget(self.color_button)

        self.motion_button = QPushButton("Motion Recording")
        self.motion_button.setCheckable(True)
        self.motion_button.setChecked(True)
        self.motion_button.toggled.connect(self.toggle_motion_button)
        layout.addWidget(self.motion_button)

        layout.addWidget(QLabel("Spessore rettangolo"))
        self.thickness_slider = QSlider(Qt.Horizontal)
        self.thickness_slider.setRange(1, 10)
        self.thickness_slider.setValue(self.rect_thickness)
        self.thickness_slider.valueChanged.connect(self.update_thickness)
        layout.addWidget(self.thickness_slider)

        layout.addWidget(QLabel("Zoom"))
        self.zoom_slider = QSlider(Qt.Horizontal)
        self.zoom_slider.setRange(10, 200)
        self.zoom_slider.setValue(100)
        self.zoom_slider.valueChanged.connect(self.update_zoom)
        layout.addWidget(self.zoom_slider)
        group.setLayout(layout)
        group.setMaximumWidth(380)
        return group

    def create_yolo_group(self):
        """Create YOLO object detector control group."""
        group = QGroupBox("Rilevamento Oggetti (YOLO)")
        layout = QVBoxLayout()

        # YOLO toggle button
        self.yolo_button = QPushButton("Rilevamento YOLO: ON")
        self.yolo_button.setCheckable(True)
        self.yolo_button.setChecked(True)
        self.yolo_button.setStyleSheet("background-color: #28a745; color: white;")
        self.yolo_button.toggled.connect(self.toggle_yolo_button)
        layout.addWidget(self.yolo_button)

        # Label for YOLO detector
        layout.addWidget(QLabel("Rilevatore: Neural Network (YOLOv8n)"))

        # Color button for YOLO boxes
        self.yolo_color_button = QPushButton("Colore box rilevamento")
        self.yolo_color_button.clicked.connect(self.choose_yolo_color)
        layout.addWidget(self.yolo_color_button)

        # Thickness slider for YOLO boxes
        layout.addWidget(QLabel("Spessore linea"))
        self.yolo_thickness_slider = QSlider(Qt.Horizontal)
        self.yolo_thickness_slider.setRange(1, 10)
        self.yolo_thickness_slider.setValue(self.yolo_rect_thickness)
        self.yolo_thickness_slider.valueChanged.connect(self.update_yolo_thickness)
        layout.addWidget(self.yolo_thickness_slider)

        group.setLayout(layout)
        group.setMaximumWidth(380)
        return group

    def create_feedback_group(self):
        group = QGroupBox("Feedback")
        layout = QVBoxLayout()
        self.coords_check = QCheckBox("Mostra coordinate")
        self.coords_check.toggled.connect(self.toggle_coords)
        layout.addWidget(self.coords_check)

        self.fps_check = QCheckBox("Mostra FPS")
        self.fps_check.setChecked(True)
        self.fps_check.toggled.connect(self.toggle_fps)
        layout.addWidget(self.fps_check)

        self.gray_button = QPushButton("Filtro bianco e nero: OFF")
        self.gray_button.clicked.connect(self.toggle_gray_filter)
        layout.addWidget(self.gray_button)

        self.snapshot_button = QPushButton("Salva snapshot")
        self.snapshot_button.clicked.connect(self.save_snapshot)
        layout.addWidget(self.snapshot_button)

        self.photo_label = QLabel(f"Foto scattate: {self.photo_count}")
        layout.addWidget(self.photo_label)
        self.video_label_widget = QLabel(f"Video registrati: {self.video_count}")
        layout.addWidget(self.video_label_widget)
        self.last_photo_label = QLabel(f"Ultima foto: {self.last_photo}")
        layout.addWidget(self.last_photo_label)
        self.last_video_label = QLabel(f"Ultimo video: {self.last_video}")
        layout.addWidget(self.last_video_label)
        group.setLayout(layout)
        group.setMaximumWidth(380)
        return group

    def create_savepath_group(self):
        group = QGroupBox("Percorso salvataggio")
        layout = QVBoxLayout()
        self.path_label = QLabel(self.save_path)
        layout.addWidget(self.path_label)
        self.change_path_button = QPushButton("Cambia")
        self.change_path_button.clicked.connect(self.change_save_path)
        layout.addWidget(self.change_path_button)
        group.setLayout(layout)
        group.setMaximumWidth(380)
        return group

    def create_theme_group(self):
        group = QGroupBox("Tema")
        layout = QVBoxLayout()
        self.theme_combo = QComboBox()
        # Show in Italian for clarity
        self.theme_combo.addItem("Sistema", ThemeMode.SYSTEM.value)
        self.theme_combo.addItem("Chiaro", ThemeMode.LIGHT.value)
        self.theme_combo.addItem("Scuro", ThemeMode.DARK.value)
        # initialize selection from settings
        cur = settings_manager.get_theme_mode()
        idx = 0
        for i in range(self.theme_combo.count()):
            if self.theme_combo.itemData(i) == cur:
                idx = i
                break
        self.theme_combo.setCurrentIndex(idx)
        self.theme_combo.currentIndexChanged.connect(self.on_theme_changed)
        layout.addWidget(self.theme_combo)
        # Color picker for 'details' (primary accent)
        self.detail_color_button = QPushButton("Colore dettagli")
        self.detail_color_button.clicked.connect(self.choose_detail_color)
        layout.addWidget(self.detail_color_button)
        group.setLayout(layout)
        group.setMaximumWidth(380)
        return group

    def create_object_group(self):
        group = QGroupBox("Riconoscimento Oggetti")
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Clicca sul video per selezionare un oggetto (clic di nuovo per deselezionare)"))

        hbox = QHBoxLayout()
        self.label_input = QLineEdit()
        self.label_input.setPlaceholderText("es. Telefono, Tazza rossa...")
        hbox.addWidget(self.label_input)

        btn_label = QPushButton("Salva oggetto selezionato")
        btn_label.clicked.connect(self.on_label_object)
        hbox.addWidget(btn_label)
        layout.addLayout(hbox)

        btn_clear = QPushButton("Cancella tutti i modelli")
        btn_clear.clicked.connect(self.clear_known_objects)
        layout.addWidget(btn_clear)

        group.setLayout(layout)
        group.setMaximumWidth(380)
        return group

    # ========================================================================
    # AZIONI CONTROLLI
    # ========================================================================
    def change_save_path(self):
        folder = QFileDialog.getExistingDirectory(self, "Scegli cartella")
        if folder:
            self.save_path = folder
            self.path_label.setText(folder)
            self.save_stats()

    def on_theme_changed(self, index: int):
        mode = self.theme_combo.itemData(index)
        try:
            settings_manager.set_theme_mode(mode)
        except Exception:
            pass

    def choose_detail_color(self):
        # Open QColorDialog to choose primary/accent color
        try:
            current = settings_manager.get_theme_colors().primary
            color = QColor(current)
            picked = QColorDialog.getColor(color, self, "Scegli colore dettagli")
            if picked.isValid():
                hexc = picked.name()
                settings_manager.set_custom_color('primary', hexc)
                qss = ThemeEngine.generate_stylesheet(settings_manager.get_theme_colors())
                QApplication.instance().setStyleSheet(qss)
        except Exception:
            pass
        # Apply stylesheet immediately
        try:
            qss = ThemeEngine.generate_stylesheet(settings_manager.get_theme_colors())
            QApplication.instance().setStyleSheet(qss)
        except Exception:
            pass

    def toggle_sidebar(self):
        # Toggle the whole sidebar widget visibility and update the small toggle icon
        if self.sidebar_widget.isVisible():
            self.sidebar_widget.hide()
            self.toggle_sidebar_button.setText("⚙")
            self.toggle_sidebar_button.setToolTip("Mostra impostazioni")
        else:
            self.sidebar_widget.show()
            self.toggle_sidebar_button.setText("←")
            self.toggle_sidebar_button.setToolTip("Nascondi impostazioni")
        self.update()

    def change_camera(self, index):
        if index < 0 or index >= self.cam_selector.count():
            return
        # Release current capture if necessary
        try:
            if self.cap is not None and self.cap.isOpened():
                self.cap.release()
        except Exception:
            pass

        if index == len(self.available_indices):  # Opzione "Camera Telefono"
            url = self.phone_url_input.text().strip() or "http://10.30.23.5:8080/video"
            # Prefer FFMPEG backend for network streams; fallback to default if not available
            opened = False
            try:
                self.cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
                opened = self.cap.isOpened()
            except Exception:
                opened = False

            if not opened:
                # Try without specifying backend
                self.cap = cv2.VideoCapture(url)
                opened = self.cap.isOpened()

            if not opened:
                QMessageBox.warning(self, "Errore", "Impossibile connettere alla camera del telefono. Verifica l'URL e la connessione.")
                # Try to reopen previous local camera
                try:
                    self.cap, _ = open_camera_with_fallback(self.current_cam_index)
                except Exception:
                    self.cap = None
                return

            self.current_cam_name = "Camera Telefono"
            # mark a sentinel index for phone stream
            self.current_cam_index = -1
        else:
            new_index = self.available_indices[index]
            new_name = self.available_names[index]
            
            # Use fallback mechanism for camera opening
            self.cap, backend = open_camera_with_fallback(new_index)
            
            if self.cap is None or not self.cap.isOpened():
                QMessageBox.warning(self, "Errore", "Impossibile aprire la webcam selezionata.")
                return
            
            self.current_cam_index = new_index
            self.current_cam_name = new_name
            self.current_backend = backend
            
        # restart frame grabber to use the new capture object
        try:
            if hasattr(self, 'frame_grabber') and self.frame_grabber:
                self.frame_grabber.stop()
        except Exception:
            pass

        try:
            self.frame_grabber = FrameGrabber(self.cap)
            self.frame_grabber.start()
        except Exception:
            pass

        self.cam_name_label.setText(f"Webcam attiva: {self.current_cam_name}")

    def choose_color(self):
        color = QColorDialog.getColor(self.rect_color, self, "Scegli colore")
        if color.isValid():
            self.rect_color = color

    def update_thickness(self, value):
        self.rect_thickness = value

    def update_zoom(self, value):
        self.zoom_factor = value / 100.0

    def toggle_coords(self, checked):
        self.show_coords = checked

    def toggle_fps(self, checked):
        self.show_fps = checked

    def toggle_camera(self):
        if self.running:
            self.timer.stop()
            self.video_label.clear()
            self.start_button.setText("Start Camera")
            self.start_button.setStyleSheet("background-color: green; color: white;")
        else:
            # If the user has selected the phone camera option, ensure it's opened now
            try:
                current_idx = self.cam_selector.currentIndex()
            except Exception:
                current_idx = -999

            if current_idx == len(self.available_indices):
                # attempt to (re)open phone stream using current URL
                self.change_camera(current_idx)
                if not (self.cap and self.cap.isOpened()):
                    QMessageBox.warning(self, "Errore", "Impossibile aprire lo stream del telefono. Verifica l'URL e la rete.")
                    return

            # use a slightly lower update rate to reduce CPU usage
            self.timer.start(40)
            self.start_button.setText("Stop Camera")
            self.start_button.setStyleSheet("background-color: red; color: white;")
        self.running = not self.running

    def toggle_gray_filter(self):
        self.gray_filter = not self.gray_filter
        if self.gray_filter:
            self.gray_button.setText("Filtro bianco e nero: ON")
            self.gray_button.setStyleSheet("background-color: #444444; color: white;")
        else:
            self.gray_button.setText("Filtro bianco e nero: OFF")
            self.gray_button.setStyleSheet("")

    def toggle_motion_button(self, checked):
        self.motion_enabled = checked
        if checked:
            self.motion_button.setText("Motion Recording: ON")
            self.motion_button.setStyleSheet("background-color: #28a745; color: white;")
        else:
            self.motion_button.setText("Motion Recording: OFF")
            self.motion_button.setStyleSheet("background-color: #6c757d; color: white;")
            self.prev_gray = None

    def toggle_yolo_button(self, checked):
        """Toggle YOLO object detection on/off."""
        self.yolo_enabled = checked
        if checked:
            self.yolo_button.setText("Rilevamento YOLO: ON")
            self.yolo_button.setStyleSheet("background-color: #28a745; color: white;")
        else:
            self.yolo_button.setText("Rilevamento YOLO: OFF")
            self.yolo_button.setStyleSheet("background-color: #6c757d; color: white;")
            self.yolo_results_cache = []  # Clear cache when disabled

    def choose_yolo_color(self):
        """Open color dialog for YOLO box color."""
        color = QColorDialog.getColor(self.yolo_rect_color, self, "Scegli colore box YOLO")
        if color.isValid():
            self.yolo_rect_color = color

    def update_yolo_thickness(self, value):
        """Update YOLO box thickness from slider."""
        self.yolo_rect_thickness = value

    # ========================================================================
    # REGISTRAZIONE VIDEO
    # ========================================================================
    def toggle_recording(self):
        if not self.running:
            QMessageBox.warning(self, "Errore", "Avvia prima la fotocamera.")
            return

        if self.recording:
            self.recording = False
            self.record_button.setText("Start Recording")
            self.record_button.setStyleSheet("background-color: #173c68; color: white;")
            if self.video_writer:
                self.video_writer.release()
                self.video_writer = None

            duration_sec = int(time.time() - self.recording_start_time) if self.recording_start_time else 0
            duration_str = time.strftime("%H:%M:%S", time.gmtime(duration_sec))

            logger.info(
                "Registrazione TERMINATA | durata=%s | frame con volti=%d | luogo=%s",
                duration_str, self.face_detection_counter, self.location
            )

            self.last_video = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            self.last_video_label.setText(f"Ultimo video: {self.last_video}")
            self.save_stats()
            QMessageBox.information(self, "Registrazione", "Video salvato!")
            self.face_detection_counter = 0
            self.recording_start_time = None
        else:
            filename = datetime.datetime.now().strftime("record_%Y%m%d_%H%M%S.mp4")
            full_path = os.path.join(self.save_path, filename)
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            # Some network streams (e.g. IP Webcam) may not report width/height via properties.
            # Fallback to the last_frame dimensions if available.
            if (w == 0 or h == 0) and self.last_frame is not None:
                h, w = self.last_frame.shape[:2]

            # Use a conservative fps for saving to reduce CPU usage during encoding
            target_fps = 20
            try:
                cur_fps = int(self.fps)
                if 8 <= cur_fps <= 30:
                    target_fps = cur_fps
            except Exception:
                pass

            self.video_writer = cv2.VideoWriter(full_path, fourcc, target_fps, (w, h))

            if not self.video_writer.isOpened():
                QMessageBox.warning(self, "Errore", "Impossibile creare il video.")
                return

            self.recording = True
            self.recording_start_time = time.time()
            self.record_start_time = time.time()
            self.face_detection_counter = 0
            self.video_count += 1
            self.video_label_widget.setText(f"Video registrati: {self.video_count}")
            self.record_button.setText("Stop Recording")
            self.record_button.setStyleSheet("background-color: red; color: white;")
            self.save_stats()

            logger.info("Registrazione INIZIATA | file=%s | luogo=%s", filename, self.location)

    # ========================================================================
    # SNAPSHOT
    # ========================================================================
    def save_snapshot(self):
        try:
            ret, frame = self.cap.read()
            if not ret:
                return
            frame = cv2.flip(frame, 1)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            filename = datetime.datetime.now().strftime("snapshot_%Y%m%d_%H%M%S.png")
            full_path = os.path.join(self.save_path, filename)
            if cv2.imwrite(full_path, gray):
                self.photo_count += 1
                self.last_photo = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                self.photo_label.setText(f"Foto scattate: {self.photo_count}")
                self.last_photo_label.setText(f"Ultima foto: {self.last_photo}")
                self.save_stats()
                QMessageBox.information(self, "Snapshot", "Foto salvata!")
            else:
                QMessageBox.warning(self, "Errore", "Impossibile salvare immagine.")
        except Exception as e:
            logger.error(f"Errore snapshot: {e}")
            QMessageBox.warning(self, "Errore", str(e))

    # ========================================================================
    # UPDATE FRAME (CUORE DELL'APPLICAZIONE)
    # ========================================================================
    def update_frame(self):
        # Read latest frame from background grabber to avoid blocking UI
        frame = None
        try:
            frame = self.frame_grabber.get_frame()
        except Exception:
            frame = None

        if frame is None:
            return

        frame = cv2.flip(frame, 1)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        if self.gray_filter:
            frame = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)

        # Zoom
        if self.zoom_factor > 1.0:
            h, w = frame.shape[:2]
            new_w = int(w / self.zoom_factor)
            new_h = int(h / self.zoom_factor)
            x1 = (w - new_w) // 2
            y1 = (h - new_h) // 2
            frame = frame[y1:y1+new_h, x1:x1+new_w]
            frame = cv2.resize(frame, (w, h), interpolation=cv2.INTER_LINEAR)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Motion detection on downscaled frame for speed
        if self.motion_enabled:
            small = cv2.resize(gray, (0, 0), fx=0.5, fy=0.5)
            if self.prev_gray is None:
                self.prev_gray = small.copy()
            else:
                delta = cv2.absdiff(self.prev_gray, small)
                thresh = cv2.threshold(delta, 25, 255, cv2.THRESH_BINARY)[1]
                motion_pixels = cv2.countNonZero(thresh)

                if motion_pixels > max(500, int(self.motion_threshold * 0.25)):
                    self.motion_last_seen = time.time()
                    if not self.recording:
                        self.toggle_recording()
                        self.motion_recording_active = True
                else:
                    if (self.motion_recording_active and self.recording and
                        time.time() - self.motion_last_seen > self.motion_grace_seconds):
                        self.toggle_recording()
                        self.motion_recording_active = False
                self.prev_gray = small.copy()

        # Rilevamento volti
        faces = self.detector.detectMultiScale(gray, 1.3, 5, minSize=(40,40))
        if self.recording and len(faces) > 0:
            self.face_detection_counter += 1

        for (x,y,w,h) in faces:
            cv2.rectangle(frame, (x,y), (x+w,y+h),
                         (self.rect_color.blue(), self.rect_color.green(), self.rect_color.red()),
                         self.rect_thickness)
            if self.show_coords:
                cv2.putText(frame, f"{x},{y}", (x,y-10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255), 1)

        # FPS
        now = time.time()
        self.fps = 1.0 / max(now - self.prev_time, 0.0001)
        self.prev_time = now
        if self.show_fps:
            cv2.putText(frame, f"FPS: {int(self.fps)}", (10,30),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,255), 2)

        # Data
        date_str = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        cv2.putText(frame, date_str, (10, frame.shape[0]-10),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200,200,200), 2)

        # Registrazione overlay
        if self.recording and self.video_writer:
            elapsed = int(time.time() - self.record_start_time)
            timer_str = time.strftime("%H:%M:%S", time.gmtime(elapsed))

            cv2.circle(frame, (20,60), 10, (0,0,255), -1)
            cv2.putText(frame, "REC", (40,65), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,0,255), 2)
            cv2.putText(frame, timer_str, (100,65), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255,255,255), 2)

            tw, _ = cv2.getTextSize(timer_str, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)[0]
            cv2.putText(frame, self.location, (100 + tw + 12, 65),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200,200,200), 2)

            self.video_writer.write(frame)
        else:
            cv2.putText(frame, self.location, (10, frame.shape[0]-40),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200,200,200), 2)

        # Rilevamento oggetti con YOLO in background to avoid UI blocking
        self.frame_counter += 1
        if self.yolo_enabled:
            # Submit a job every yolo_freq frames if none is running
            if (self.frame_counter % self.yolo_freq) == 0 and (self.yolo_future is None or self.yolo_future.done()):
                try:
                    h_orig, w_orig = frame.shape[:2]
                    small_frame = cv2.resize(frame, (640, 480))
                    # submit inference to background thread via lambda to ensure keyword args are respected
                    self._yolo_scale = (w_orig / 640.0, h_orig / 480.0)
                    self.yolo_future = self.yolo_executor.submit(lambda sf=small_frame: self.yolo_model(sf, verbose=False, conf=0.45))
                except Exception as e:
                    logger.warning(f"YOLO submit failed: {e}")
                    self.yolo_future = None

            # If previous job finished, fetch and cache results
            if self.yolo_future is not None and self.yolo_future.done():
                try:
                    raw = self.yolo_future.result()
                    # ultralytics may return a Results object or a list; normalize to iterable
                    if hasattr(raw, 'boxes'):
                        results_iter = [raw]
                    elif isinstance(raw, (list, tuple)):
                        results_iter = list(raw)
                    else:
                        results_iter = [raw]

                    scale_x, scale_y = getattr(self, '_yolo_scale', (1.0, 1.0))
                    new_cache = []
                    for r in results_iter:
                        # each r should have .boxes and .names
                        boxes = getattr(r, 'boxes', None)
                        names = getattr(r, 'names', {})
                        if boxes is None:
                            continue
                        for box in boxes:
                            try:
                                cls = int(box.cls[0])
                                conf = float(box.conf[0])
                                x1, y1, x2, y2 = map(int, box.xyxy[0])
                                x1 = int(x1 * scale_x)
                                y1 = int(y1 * scale_y)
                                x2 = int(x2 * scale_x)
                                y2 = int(y2 * scale_y)
                                label = f"{names.get(cls, cls)} {conf:.2f}"
                                new_cache.append({'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2, 'label': label})
                            except Exception:
                                continue
                    self.yolo_results_cache = new_cache
                except Exception as e:
                    logger.warning(f"YOLO result handling failed: {e}")
                    self.yolo_results_cache = []
                    self.yolo_future = None

            # Draw cached results on all frames
            for detection in self.yolo_results_cache:
                cv2.rectangle(frame, (detection['x1'], detection['y1']), (detection['x2'], detection['y2']), 
                            (self.yolo_rect_color.blue(), self.yolo_rect_color.green(), self.yolo_rect_color.red()),
                            self.yolo_rect_thickness)
                cv2.putText(frame, detection['label'], (detection['x1'], detection['y1'] - 10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, 
                           (self.yolo_rect_color.blue(), self.yolo_rect_color.green(), self.yolo_rect_color.red()), 2)

        # Disegna rettangolo selezione oggetto
        if self.selected_rect:
            x, y, w, h = self.selected_rect
            cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)  # blu

        # Visualizzazione
        self.last_frame = frame.copy()
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        qimg = QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qimg).scaled(
            self.video_label.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        self.video_label.setPixmap(pixmap)

    # ========================================================================
    # GESTIONE CLICK PER SELEZIONE OGGETTO
    # ========================================================================
    def handle_object_click(self, pos):
        if self.last_frame is None or not self.running:
            return

        # Calcola posizione nel frame originale considerando lo scaling e aspect ratio
        label_size = self.video_label.size()
        pixmap = self.video_label.pixmap()
        if not pixmap:
            return
        pixmap_size = pixmap.size()

        h_frame, w_frame = self.last_frame.shape[:2]
        aspect_frame = w_frame / h_frame
        aspect_label = label_size.width() / label_size.height()

        if aspect_frame > aspect_label:
            # Barre verticali
            draw_width = label_size.width()
            draw_height = int(draw_width / aspect_frame)
            x_offset = 0
            y_offset = (label_size.height() - draw_height) // 2
        else:
            # Barre orizzontali
            draw_height = label_size.height()
            draw_width = int(draw_height * aspect_frame)
            x_offset = (label_size.width() - draw_width) // 2
            y_offset = 0

        click_x = pos.x() - x_offset
        click_y = pos.y() - y_offset

        if click_x < 0 or click_x >= draw_width or click_y < 0 or click_y >= draw_height:
            return  # Click fuori area video

        scale_x = w_frame / draw_width
        scale_y = h_frame / draw_height
        frame_x = int(click_x * scale_x)
        frame_y = int(click_y * scale_y)

        # Se già selezionato, deseleziona
        if self.selected_rect:
            self.selected_rect = None
            return

        # Altrimenti, rileva oggetto con floodFill
        frame_copy = self.last_frame.copy()
        seed = (frame_x, frame_y)
        h, w = frame_copy.shape[:2]
        mask = np.zeros((h + 2, w + 2), np.uint8)

        # Flood fill parameters: loDiff and upDiff for color tolerance
        cv2.floodFill(frame_copy, mask, seed, (255, 0, 0), (20, 20, 20), (20, 20, 20), flags=cv2.FLOODFILL_MASK_ONLY)

        mask = mask[1:h+1, 1:w+1]

        # Find contours on the mask
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if contours:
            # Find the contour that contains the seed point
            for cnt in contours:
                if cv2.pointPolygonTest(cnt, (frame_x, frame_y), False) >= 0:
                    x, y, w, h = cv2.boundingRect(cnt)
                    if w > 20 and h > 20:  # Min size filter
                        self.selected_rect = (x, y, w, h)
                    break

    # ========================================================================
    # RICONOSCIMENTO OGGETTI
    # ========================================================================
    def load_known_objects(self):
        self.known_descriptors.clear()
        for npz_file in KNOWN_OBJECTS_DIR.glob("*.npz"):
            try:
                data = np.load(npz_file, allow_pickle=True)
                name = str(data.get("name", ""))
                des = data.get("des")
                if des is not None and len(des) > 20:
                    self.known_descriptors[name] = (des, npz_file.stem)
            except Exception as e:
                logger.warning(f"Errore caricamento {npz_file}: {e}")

    def save_labeled_object(self, name, crop_bgr):
        if not name.strip():
            QMessageBox.warning(self, "Errore", "Inserisci un nome valido.")
            return False

        # Reduce ORB features to lower CPU/memory usage
        orb = cv2.ORB_create(nfeatures=600)
        kp, des = orb.detectAndCompute(crop_bgr, None)

        if des is None or len(des) < 40:
            QMessageBox.warning(self, "Attenzione",
                                "Pochi punti caratteristici rilevati.\n"
                                "Prova con più contrasto/luce o oggetto più grande.")
            return False

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = "".join(c for c in name if c.isalnum() or c in " _-").strip()
        filename = f"{safe_name}_{timestamp}.npz"
        path = KNOWN_OBJECTS_DIR / filename

        # Salva anche immagine di riferimento
        ref_path = KNOWN_OBJECTS_DIR / f"{safe_name}_{timestamp}_ref.png"
        cv2.imwrite(str(ref_path), crop_bgr)

        np.savez(path,
                 name=name,
                 des=des,
                 timestamp=timestamp,
                 ref_filename=str(ref_path.name))

        self.known_descriptors[name] = (des, filename[:-4])

        QMessageBox.information(self, "Successo", f"Oggetto '{name}' salvato!")
        return True

    def recognize_object(self, gray):
        if not self.known_descriptors:
            return None
        orb = cv2.ORB_create(nfeatures=600)
        kp_frame, des_frame = orb.detectAndCompute(gray, None)
        if des_frame is None or len(des_frame) < 40:
            return None

        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)

        best_name = None
        best_count = 0
        best_score = 0

        for name, (des_ref, _) in self.known_descriptors.items():
            if len(des_ref) < 30:
                continue

            matches = bf.match(des_frame, des_ref)
            good = [m for m in matches if m.distance < MATCH_DISTANCE_THRESHOLD]
            good_count = len(good)

            if good_count > best_count:
                score = good_count / min(len(des_frame), len(des_ref))
                if good_count >= MIN_GOOD_MATCHES and score > best_score:
                    best_count = good_count
                    best_score = score
                    best_name = name

        if best_count >= MIN_GOOD_MATCHES and best_score > MIN_SCORE:
            return f"{best_name} ({best_count} match, {best_score:.2f})"
        return None

    def on_label_object(self):
        if self.last_frame is None or not self.running:
            QMessageBox.warning(self, "Attenzione", "Avvia la camera.")
            return

        name = self.label_input.text().strip()
        if self.selected_rect:
            x, y, w, h = self.selected_rect
            crop = self.last_frame[y:y+h, x:x+w]
            if crop.size == 0:
                QMessageBox.warning(self, "Errore", "Selezione vuota.")
                return
        else:
            crop = self.last_frame

        if self.save_labeled_object(name, crop):
            self.label_input.clear()
            self.selected_rect = None  # Reset dopo salvataggio

    def clear_known_objects(self):
        reply = QMessageBox.question(self, "Conferma",
                                    "Cancellare tutti gli oggetti salvati?",
                                    QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            for f in KNOWN_OBJECTS_DIR.glob("*.*"):
                f.unlink(missing_ok=True)
            self.load_known_objects()
            QMessageBox.information(self, "Fatto", "Tutti i modelli sono stati cancellati.")

    def closeEvent(self, event):
        if self.timer.isActive():
            self.timer.stop()
        if self.cap.isOpened():
            self.cap.release()
        if self.video_writer:
            self.video_writer.release()
        # Stop background frame grabber and YOLO executor
        try:
            if hasattr(self, 'frame_grabber') and self.frame_grabber:
                self.frame_grabber.stop()
        except Exception:
            pass

        try:
            if hasattr(self, 'yolo_executor') and self.yolo_executor:
                self.yolo_executor.shutdown(wait=False)
        except Exception:
            pass
        event.accept()

# =============================================================================================
# ENTRY POINT
# =============================================================================================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    # Apply theme from settings (generated QSS)
    try:
        qss = ThemeEngine.generate_stylesheet(settings_manager.get_theme_colors())
        app.setStyleSheet(qss)
    except Exception:
        pass

    window = FaceApp()
    window.show()
    sys.exit(app.exec())
