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
from ultralytics import YOLO

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

# =============================================================================================
# SUBCLASS PER QLabel CLICCABILE
# =============================================================================================
class ClickableLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self.parent().handle_object_click(event.pos())

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

        # Webcam
        self.available_indices, self.available_names = self.scan_webcams()
        if not self.available_indices:
            raise RuntimeError("Nessuna webcam trovata.")

        self.current_cam_index = self.available_indices[0]
        self.current_cam_name = self.available_names[0]
        self.cap = cv2.VideoCapture(self.current_cam_index, cv2.CAP_MSMF)
        if not self.cap.isOpened():
            raise RuntimeError("Impossibile aprire la webcam principale.")

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
        settings_layout.addWidget(self.create_object_group())
        settings_layout.addStretch()

        settings_container = QWidget()
        settings_container.setLayout(settings_layout)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(settings_container)
        self.scroll_area = scroll_area

        sidebar_layout = QVBoxLayout()
        self.toggle_sidebar_button = QPushButton("Nascondi impostazioni")
        self.toggle_sidebar_button.clicked.connect(self.toggle_sidebar)
        sidebar_layout.addWidget(self.toggle_sidebar_button)
        sidebar_layout.addWidget(scroll_area, 1)

        sidebar_widget = QWidget()
        sidebar_widget.setLayout(sidebar_layout)
        sidebar_widget.setFixedWidth(330)
        self.sidebar_widget = sidebar_widget

        # Layout principale
        video_layout = QVBoxLayout()
        video_layout.addWidget(self.cam_name_label)
        video_layout.addWidget(self.video_label)

        main_layout = QHBoxLayout(self)
        main_layout.addWidget(self.sidebar_widget, 0)
        main_layout.addLayout(video_layout, 1)

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
        indices = []
        names = []
        for i in range(10):
            try:
                cap = cv2.VideoCapture(i, cv2.CAP_MSMF)
                if cap.isOpened():
                    ret, _ = cap.read()
                    if ret:
                        indices.append(i)
                        names.append(f"Webcam {i}")
                    cap.release()
            except:
                continue
        return indices, names

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

        self.start_button = QPushButton("Start Camera")
        self.start_button.clicked.connect(self.toggle_camera)
        self.start_button.setStyleSheet("background-color: green; color: white;")
        layout.addWidget(self.start_button)

        self.record_button = QPushButton("Start Recording")
        self.record_button.clicked.connect(self.toggle_recording)
        self.record_button.setStyleSheet("background-color: #173c68; color: white;")
        layout.addWidget(self.record_button)
        group.setLayout(layout)
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

    def toggle_sidebar(self):
        if self.scroll_area.isVisible():
            self.scroll_area.hide()
            self.toggle_sidebar_button.setText("Mostra impostazioni")
        else:
            self.scroll_area.show()
            self.toggle_sidebar_button.setText("Nascondi impostazioni")
        self.update()

    def change_camera(self, index):
        if index < 0 or index >= self.cam_selector.count():
            return

        if self.cap.isOpened():
            self.cap.release()

        if index == len(self.available_indices):  # Opzione "Camera Telefono"
            url = self.phone_url_input.text().strip() or "http://10.30.23.5:8080/video"  # Default dal messaggio utente
            self.cap = cv2.VideoCapture(url)
            if not self.cap.isOpened():
                QMessageBox.warning(self, "Errore", "Impossibile connettere alla camera del telefono. Verifica l'URL e la connessione.")
                self.cap = cv2.VideoCapture(self.current_cam_index)  # Torna alla default
                return
            self.current_cam_name = "Camera Telefono"
        else:
            new_index = self.available_indices[index]
            new_name = self.available_names[index]
            self.cap = cv2.VideoCapture(new_index, cv2.CAP_MSMF)
            if not self.cap.isOpened():
                QMessageBox.warning(self, "Errore", "Impossibile aprire la webcam selezionata.")
                return
            self.current_cam_index = new_index
            self.current_cam_name = new_name

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
            self.timer.start(30)
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
            self.video_writer = cv2.VideoWriter(full_path, fourcc, 30, (w, h))

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
        ret, frame = self.cap.read()
        if not ret:
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

        # Motion detection
        if self.motion_enabled:
            if self.prev_gray is None:
                self.prev_gray = gray.copy()
            else:
                delta = cv2.absdiff(self.prev_gray, gray)
                thresh = cv2.threshold(delta, 25, 255, cv2.THRESH_BINARY)[1]
                motion_pixels = cv2.countNonZero(thresh)

                if motion_pixels > self.motion_threshold:
                    self.motion_last_seen = time.time()
                    if not self.recording:
                        self.toggle_recording()
                        self.motion_recording_active = True
                else:
                    if (self.motion_recording_active and self.recording and
                        time.time() - self.motion_last_seen > self.motion_grace_seconds):
                        self.toggle_recording()
                        self.motion_recording_active = False
                self.prev_gray = gray.copy()

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

        # Rilevamento oggetti con YOLO (ogni 3 frame per performance)
        self.frame_counter += 1
        if self.yolo_enabled:
            if self.frame_counter % 3 == 0:
                # Run YOLO on optimized resolution (960x720) for balance between accuracy and speed
                h_orig, w_orig = frame.shape[:2]
                small_frame = cv2.resize(frame, (960, 720))
                results = self.yolo_model(small_frame, verbose=False, conf=0.45)
                
                # Scale factors to map detections back to original frame
                scale_x = w_orig / 960.0
                scale_y = h_orig / 720.0
                
                # Cache the results
                self.yolo_results_cache = []
                for r in results:
                    for box in r.boxes:
                        cls = int(box.cls[0])
                        conf = box.conf[0]
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        # Scale coordinates back to original frame
                        x1 = int(x1 * scale_x)
                        y1 = int(y1 * scale_y)
                        x2 = int(x2 * scale_x)
                        y2 = int(y2 * scale_y)
                        self.yolo_results_cache.append({
                            'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2,
                            'label': f"{r.names[cls]} {conf:.2f}"
                        })
            
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

        orb = cv2.ORB_create(nfeatures=1200)  # aumentato perché frame intero
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

        orb = cv2.ORB_create(nfeatures=1200)
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
        event.accept()

# =============================================================================================
# ENTRY POINT
# =============================================================================================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    try:
        with open("style.qss", "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())
    except FileNotFoundError:
        pass

    window = FaceApp()
    window.show()
    sys.exit(app.exec())