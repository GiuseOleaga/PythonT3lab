# ====================================================================================================================================================================================================================================
# APPLICAZIONE DI ACCESSO BIOMETRICO - Face Detection & Recording System ====================================================================================================================================================
# ====================================================================================================================================================================================================================================

# ========================================================================================================================================================================================================================
# PRIMARY SECTION: IMPORTS ========================================================================================================================================================================================
# ========================================================================================================================================================================================================================
import sys
import os
import json
import cv2
import time
import datetime
import geocoder

from PySide6.QtWidgets import (
    QApplication, QLabel, QPushButton, QVBoxLayout, QWidget,
    QHBoxLayout, QGroupBox, QColorDialog, QCheckBox, QSlider,
    QComboBox, QFileDialog, QMessageBox, QSizePolicy, QScrollArea
)
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QImage, QPixmap, QColor

# ========================================================================================================================================================================================================================
# PRIMARY SECTION: CONSTANTS========================================================================================================================================================================================
# ========================================================================================================================================================================================================================
STATS_FILE = "stats.json"


# ========================================================================================================================================================================================================================
# APPLICAZIONE MAIN ========================================================================================================================================================================================
# ========================================================================================================================================================================================================================
class FaceApp(QWidget):

    # ============================================================================================
    # INIZZIALIZZAZIONE DELL'APPLICAZIONE, CON CONFIGURAZIONE DELLA FINESTRA
    # ============================================================================================
    def __init__(self):
        super().__init__()
        
        # ---- configurazione della finestra principale ----
        self.setWindowTitle("APPLICAZIONE DI ACCESSO BIOMETRICO")
        self.resize(1100, 600)
        self.setMinimumSize(900, 500)

        # ---- parametri base ----
        self.rect_color = QColor(0, 255, 0)
        self.rect_thickness = 2
        self.show_coords = False
        self.show_fps = True
        self.zoom_factor = 1.0
        self.last_frame = None
        
        # ---- filtri video ----
        self.gray_filter = False


        # ---- stato di registrazione ----
        self.recording = False
        self.video_writer = None
        self.record_start_time = None

        # ---- statisctiche ----
        self.photo_count = 0
        self.video_count = 0
        self.last_photo = "Nessuna"
        self.last_video = "Nessuno"
        self.save_path = os.getcwd()
        self.load_stats()

        # ---- geolocalizzazione ----
        try:
            g = geocoder.ip("me")
            city = g.city if g.city else "Località sconosciuta"
            country = g.country if g.country else ""
            self.location = f"{city}, {country}".strip(", ")
        except Exception:
            self.location = "Località sconosciuta"

        # ---- inizzializzazione webcam ----
        self.available_indices, self.available_names = self.scan_webcams()
        if not self.available_indices:
            raise RuntimeError("Nessuna webcam trovata.")
        
        self.current_cam_index = self.available_indices[0]
        self.current_cam_name = self.available_names[0]
        self.cap = cv2.VideoCapture(self.current_cam_index, cv2.CAP_MSMF)
        if not self.cap.isOpened():
            raise RuntimeError("Errore: impossibile aprire la webcam principale.")

        # ---- riconoscimento volto ----
        self.detector = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )

        # ---- Label del video principale ----
        self.video_label = QLabel(alignment=Qt.AlignCenter)
        self.video_label.setObjectName("video_label")
        self.video_label.setMinimumSize(0, 0)
        self.video_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        self.cam_name_label = QLabel(
            f"Webcam attiva: {self.current_cam_name}",
            alignment=Qt.AlignCenter
        )

        # ---- timer per aggiornamento frame ----
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.running = False
        self.prev_time = time.time()
        self.fps = 0

        # ---- webcam extra ----
        self.extra_caps = []
        self.extra_cam_widgets = []
        self.extra_timer = QTimer()
        self.extra_timer.timeout.connect(self.update_extra_cams)
        self.extra_timer.start(200)

        # ============================================================================================
        # BARRA LATERALE DI CONTROLLO, CON TUTTE LE IMPOSTAZIONI E STATISTICHE
        # ============================================================================================
        # barra laterale scrollabile con tutte le impostazioni e statistiche
        settings_layout = QVBoxLayout()
        settings_layout.addWidget(self.create_webcam_group())
        settings_layout.addWidget(self.create_face_group())
        settings_layout.addWidget(self.create_feedback_group())
        settings_layout.addWidget(self.create_savepath_group())
        settings_layout.addStretch()

        settings_container = QWidget()
        settings_container.setLayout(settings_layout)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(settings_container)
        self.scroll_area = scroll_area

        # barra laterale con pulsante di toggle
        sidebar_layout = QVBoxLayout()
        self.toggle_sidebar_button = QPushButton("Nascondi impostazioni")
        self.toggle_sidebar_button.clicked.connect(self.toggle_sidebar)
        sidebar_layout.addWidget(self.toggle_sidebar_button)
        sidebar_layout.addWidget(scroll_area, 1)
        
        sidebar_widget = QWidget()
        sidebar_widget.setLayout(sidebar_layout)
        sidebar_widget.setFixedWidth(330)
        self.sidebar_widget = sidebar_widget

        # ============================================================================================
        # LAYOUT PRINCIPALE: sidebar a sinistra e video a destra
        # ============================================================================================
        video_layout = QVBoxLayout()
        video_layout.addWidget(self.cam_name_label)
        video_layout.addWidget(self.video_label)

        main_layout = QHBoxLayout(self)
        main_layout.addWidget(self.sidebar_widget, 0)  # Fixed width sidebar with button always visible
        main_layout.addLayout(video_layout, 1)         # Video area takes remaining space


    # ============================================================================================
    # GESTIONE DELLE STATISTICHE DI UTILIZZO, CON CARICAMENTO E SALVATAGGIO SU FILE JSON
    # ============================================================================================
    def load_stats(self):
        """Load statistics from JSON file."""
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
        except Exception:
            pass

    def save_stats(self):
        """Save statistics to JSON file."""
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
        except Exception:
            pass

    # ============================================================================================
    # RILEVAMENTO DELLE WEBCAM DISPONIBILI SUL SISTEMA
    # ============================================================================================
    def scan_webcams(self):
        """Scan for available webcams."""
        indices = []
        names = []
        for i in range(10):
            cap = cv2.VideoCapture(i, cv2.CAP_MSMF)
            if cap.isOpened():
                indices.append(i)
                names.append(f"Webcam {i}")
                cap.release()
            else:
                cap.release()
        return indices, names

    # ============================================================================================
    # CREAZIONE DEI GRUPPI PER LA WEBCAM, RILEVAMENTO VOLTI, FEEDBACK E PERCORSO DI SALVATAGGIO
    # ============================================================================================
    def create_webcam_group(self):
        """Create webcam control group."""
        group = QGroupBox("Webcam")
        layout = QVBoxLayout()

        # selettore di webcam
        self.cam_selector = QComboBox()
        for name in self.available_names:
            self.cam_selector.addItem(name)
        self.cam_selector.currentIndexChanged.connect(self.change_camera)
        layout.addWidget(self.cam_selector)

        # bottone di avvio/stop camera
        self.start_button = QPushButton("Start Camera")
        self.start_button.clicked.connect(self.toggle_camera)
        self.start_button.setStyleSheet("background-color: green; color: white;")
        layout.addWidget(self.start_button)

        # bottone di avvio/stop registrazione
        self.record_button = QPushButton("Start Recording")
        self.record_button.clicked.connect(self.toggle_recording)
        self.record_button.setStyleSheet("background-color: #173c68; color: white;")
        layout.addWidget(self.record_button)

        group.setLayout(layout)
        return group

    def create_face_group(self):
        """Create face detection control group."""
        group = QGroupBox("Rilevamento Volti")
        layout = QVBoxLayout()

        #  bottone per scegliere il colore del rettangolo di rilevamento
        self.color_button = QPushButton("Colore rettangolo")
        self.color_button.clicked.connect(self.choose_color)
        layout.addWidget(self.color_button)

        # TERTIARY: larghezza del rettangolo di rilevamento
        layout.addWidget(QLabel("Spessore rettangolo"))
        self.thickness_slider = QSlider(Qt.Horizontal)
        self.thickness_slider.setRange(1, 10)
        self.thickness_slider.setValue(self.rect_thickness)
        self.thickness_slider.valueChanged.connect(self.update_thickness)
        layout.addWidget(self.thickness_slider)

        # Zoom Slider
        layout.addWidget(QLabel("Zoom"))
        self.zoom_slider = QSlider(Qt.Horizontal)
        self.zoom_slider.setRange(10, 200)
        self.zoom_slider.setValue(100)
        self.zoom_slider.valueChanged.connect(self.update_zoom)
        layout.addWidget(self.zoom_slider)

        group.setLayout(layout)
        return group

    def create_feedback_group(self):
        """Create feedback and statistics group."""
        group = QGroupBox("Feedback")
        layout = QVBoxLayout()

        # TERTIARY: checkbox mostra coordinate
        self.coords_check = QCheckBox("Mostra coordinate")
        self.coords_check.toggled.connect(self.toggle_coords)
        layout.addWidget(self.coords_check)

        # checkbox mostra FPS
        self.fps_check = QCheckBox("Mostra FPS")
        self.fps_check.setChecked(self.show_fps)
        self.fps_check.toggled.connect(self.toggle_fps)
        layout.addWidget(self.fps_check)

        # ---- filtro bianco e nero ----
        self.gray_button = QPushButton("Filtro bianco e nero: OFF")
        self.gray_button.clicked.connect(self.toggle_gray_filter)
        layout.addWidget(self.gray_button)

        # bottone per salvare snapshot
        self.snapshot_button = QPushButton("Salva snapshot")
        self.snapshot_button.clicked.connect(self.save_snapshot)
        layout.addWidget(self.snapshot_button)

        # label per statistiche foto e video
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
        """Create save path selection group."""
        group = QGroupBox("Percorso salvataggio")
        layout = QVBoxLayout()

        self.path_label = QLabel(self.save_path)
        layout.addWidget(self.path_label)

        self.change_path_button = QPushButton("Cambia")
        self.change_path_button.clicked.connect(self.change_save_path)
        layout.addWidget(self.change_path_button)

        group.setLayout(layout)
        return group

    # ============================================================================================
    # AZIONI PER I CONTROLLI
    # ============================================================================================
    def change_save_path(self):
        """Change the save path for photos and videos."""
        folder = QFileDialog.getExistingDirectory(self, "Scegli cartella")
        if folder:
            self.save_path = folder
            self.path_label.setText(folder)
            self.save_stats()

    def toggle_sidebar(self):
        """Toggle sidebar visibility and adjust layout."""
        if self.scroll_area.isVisible():
            self.scroll_area.hide()
            self.toggle_sidebar_button.setText("Mostra impostazioni")
        else:
            self.scroll_area.show()
            self.toggle_sidebar_button.setText("Nascondi impostazioni")
        # Update geometry so video area expands/shrinks immediately
        self.video_label.updateGeometry()
        self.update()

    def change_camera(self, index):
        """Switch to a different camera."""
        if index < 0 or index >= len(self.available_indices):
            return
        
        new_index = self.available_indices[index]
        new_name = self.available_names[index]

        if self.cap.isOpened():
            self.cap.release()

        self.cap = cv2.VideoCapture(new_index, cv2.CAP_MSMF)
        if not self.cap.isOpened():
            QMessageBox.warning(self, "Errore", "Impossibile aprire la webcam selezionata.")
            return

        self.current_cam_index = new_index
        self.current_cam_name = new_name
        self.cam_name_label.setText(f"Webcam attiva: {self.current_cam_name}")

    def choose_color(self):
        """Open color picker dialog for rectangle color."""
        color = QColorDialog.getColor(self.rect_color, self, "Scegli colore")
        if color.isValid():
            self.rect_color = color

    def update_thickness(self, value):
        """Update rectangle thickness from slider."""
        self.rect_thickness = value

    def update_zoom(self, value):
        """Update zoom factor from slider."""
        self.zoom_factor = value / 100.0

    def toggle_coords(self, checked):
        """Toggle coordinate display."""
        self.show_coords = checked

    def toggle_fps(self, checked):
        """Toggle FPS display."""
        self.show_fps = checked

    def toggle_camera(self):
        """Start or stop camera stream."""
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
        """Toggle grayscale filter on/off."""
        self.gray_filter = not self.gray_filter

        if self.gray_filter:
            self.gray_button.setText("Filtro bianco e nero: ON")
            self.gray_button.setStyleSheet("background-color: #444444; color: white;")
        else:
            self.gray_button.setText("Filtro bianco e nero: OFF")
            self.gray_button.setStyleSheet("")


    # ============================================================================================
    # REGISTRAZIONE VIDEO, con salvataggio del file
    # ============================================================================================
    def toggle_recording(self):
        """Start or stop video recording."""
        if not self.running:
            QMessageBox.warning(self, "Errore", "La camera deve essere attiva per registrare.")
            return

        if self.recording:
            # ---- stoppa la registrazione ----
            self.recording = False
            self.record_button.setText("Start Recording")
            self.record_button.setStyleSheet("background-color: #173c68; color: white;")

            if self.video_writer:
                self.video_writer.release()
                self.video_writer = None

            self.last_video = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            self.last_video_label.setText(f"Ultimo video: {self.last_video}")
            self.save_stats()
            QMessageBox.information(self, "Registrazione", "Video salvato con successo!")

        else:
            # ---- inizia la registrazione ----
            filename = datetime.datetime.now().strftime("record_%Y%m%d_%H%M%S.mp4")
            full_path = os.path.join(self.save_path, filename)

            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

            self.video_writer = cv2.VideoWriter(full_path, fourcc, 30, (w, h))

            if not self.video_writer.isOpened():
                QMessageBox.warning(self, "Errore", "Impossibile creare il file video.")
                self.video_writer = None
                return

            self.recording = True
            self.record_start_time = time.time()
            self.video_count += 1
            self.video_label_widget.setText(f"Video registrati: {self.video_count}")
            self.record_button.setText("Stop Recording")
            self.record_button.setStyleSheet("background-color: red; color: white;")
            self.save_stats()

    # ============================================================================================
    # SNAPSHOT, con salvataggio dell'immagine e aggiornamento delle statistiche
    # ============================================================================================
    def save_snapshot(self):
        """Capture and save a grayscale snapshot from the camera."""
        ret, frame = self.cap.read()
        if not ret:
            QMessageBox.warning(self, "Errore", "Impossibile catturare l'immagine.")
            return

        frame = cv2.flip(frame, 1)

        # Conversione in bianco e nero
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        filename = datetime.datetime.now().strftime("snapshot_%Y%m%d_%H%M%S.png")
        full_path = os.path.join(self.save_path, filename)

        cv2.imwrite(full_path, gray)

        self.photo_count += 1
        self.last_photo = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")

        self.photo_label.setText(f"Foto scattate: {self.photo_count}")
        self.last_photo_label.setText(f"Ultima foto: {self.last_photo}")

        self.save_stats()
        QMessageBox.information(self, "Snapshot", "Foto in bianco e nero salvata con successo!")


    # ============================================================================================
    # LOOP PRINCIPALE DI ACQUISIZIONE
    # ============================================================================================
    def update_frame(self):
        """Capture frame, process, and display on label."""
        ret, frame = self.cap.read()
        if not ret:
            return

        frame = cv2.flip(frame, 1)

        # ---- filtro bianco e nero ----
        if self.gray_filter:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)


        # ---- zoom digitale ----
        if self.zoom_factor > 1.0:
            h, w = frame.shape[:2]
            new_w = int(w / self.zoom_factor)
            new_h = int(h / self.zoom_factor)
            x1 = (w - new_w) // 2
            y1 = (h - new_h) // 2
            frame = frame[y1:y1+new_h, x1:x1+new_w]
            frame = cv2.resize(frame, (w, h), interpolation=cv2.INTER_LINEAR)

        # ---- rilavazione volto ----
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.detector.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=6)
        for (x, y, w, h) in faces:
            cv2.rectangle(
                frame, (x, y), (x+w, y+h),
                (self.rect_color.blue(), self.rect_color.green(), self.rect_color.red()),
                self.rect_thickness
            )
            if self.show_coords:
                cv2.putText(
                    frame, f"{x},{y}", (x, y-10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1
                )

        # ---- mostra FPS ----
        now = time.time()
        self.fps = 1.0 / max(now - self.prev_time, 0.0001)
        self.prev_time = now
        
        if self.show_fps:
            cv2.putText(
                frame, f"FPS: {int(self.fps)}", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2
            )

        # ---- informazioni data ----
        font = cv2.FONT_HERSHEY_SIMPLEX
        date_str = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        
        # Display date/time at bottom
        cv2.putText(
            frame, date_str, (10, frame.shape[0]-10),
            font, 0.6, (200, 200, 200), 2
        )

        # ---- mostra registrazione con tempo e luogo ----
        if self.recording and self.video_writer:
            elapsed = int(time.time() - self.record_start_time)
            timer_str = time.strftime("%H:%M:%S", time.gmtime(elapsed))
            
            # cerchio di registraizone rosso
            cv2.circle(frame, (20, 60), 10, (0, 0, 255), -1)
            
            # testo "REC" accanto al cerchio
            cv2.putText(
                frame, "REC", (40, 65),
                font, 0.7, (0, 0, 255), 2
            )
            
            # Timer
            cv2.putText(
                frame, timer_str, (100, 65),
                font, 0.8, (255, 255, 255), 2
            )
            
            # posizione del luogo a destra del timer, con calcolo dinamico della posizione in base alla lunghezza del timer
            (tx_w, tx_h), _ = cv2.getTextSize(timer_str, font, 0.8, 2)
            loc_x = 100 + tx_w + 12
            loc_y = 65
            cv2.putText(
                frame, self.location, (loc_x, loc_y),
                font, 0.6, (200, 200, 200), 2
            )
            
            # salva il frame nel video
            self.video_writer.write(frame)
        else:
            # se non stiamo registrando, mostra comunque la posizione in basso a sinistra
            cv2.putText(
                frame, self.location, (10, frame.shape[0]-40),
                font, 0.6, (200, 200, 200), 2
            )

        # ---- Convert and Display Frame ----
        # salva ultimo frame visualizzato (BGR)
        self.last_frame = frame.copy()

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        img = QImage(rgb.data, w, h, ch*w, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(img).scaled(
            self.video_label.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        self.video_label.setPixmap(pixmap)

    # ============================================================================================
    # CAMERA EXTRA (placeholder per future implementazioni di feed multipli)
    # ============================================================================================
    def update_extra_cams(self):
        """Update extra camera feeds (placeholder)."""
        pass

    # ============================================================================================
    # CLEANUP DELLE RISORSE ALLA CHIUSURA DELL'APPLICAZIONE, PER EVITARE LOCK DI WEBCAM E FILE
    # ============================================================================================
    def closeEvent(self, event):
        """Clean up resources on application close."""
        if self.timer.isActive():
            self.timer.stop()
        if self.extra_timer.isActive():
            self.extra_timer.stop()

        if self.cap.isOpened():
            self.cap.release()
        for cap in self.extra_caps:
            if cap.isOpened():
                cap.release()
        if self.video_writer:
            self.video_writer.release()

        event.accept()


# ========================================================================================================================================================================================================================
# PUNTO DI INGRESSO DELL'APP ========================================================================================================================================================================================
# ========================================================================================================================================================================================================================
if __name__ == "__main__":
    app = QApplication(sys.argv)

    # carica il file di stile QSS se presente, per migliorare l'aspetto dell'applicazione
    try:
        with open("style.qss", "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())
    except FileNotFoundError:
        pass

    # crea e mostra la finestra principale dell'applicazione
    window = FaceApp()
    window.show()

    sys.exit(app.exec())
