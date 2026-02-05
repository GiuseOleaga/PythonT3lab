import sys
import cv2
import time
import datetime

from PySide6.QtWidgets import (
    QApplication, QLabel, QPushButton, QVBoxLayout, QWidget,
    QHBoxLayout, QGroupBox, QColorDialog, QCheckBox, QSlider, QComboBox, QSizePolicy
)
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QImage, QPixmap, QColor


class FaceApp(QWidget):

    # ===================================================================================================================
    # INIZIALIZZAZIONE
    # ===================================================================================================================  

    def __init__(self):
        super().__init__()

        self.setWindowTitle("APPLICAZIONE DI ACCESSO BIOMETRICO")
        self.resize(1000, 540)
        self.setMinimumSize(800, 450)

        # Parametri --------------------------------------------------
        self.rect_color = QColor(0, 255, 0)
        self.rect_thickness = 2
        self.show_coords = False
        self.show_fps = True
        self.zoom_factor = 1.0

        # Registrazione --------------------------------------------------
        self.recording = False
        self.record_start_time = None
        self.video_writer = None

        # Scansione webcam disponibili --------------------------------------------------
        self.available_indices, self.available_names = self.scan_webcams()
        if not self.available_indices:
            raise RuntimeError("Nessuna webcam trovata.")

        # Webcam principale --------------------------------------------------
        self.current_cam_index = self.available_indices[0]
        self.cap = cv2.VideoCapture(self.current_cam_index, cv2.CAP_MSMF)
        if not self.cap.isOpened():
            raise RuntimeError("Errore: impossibile aprire la webcam principale.")

        self.current_cam_name = self.available_names[0]

        # Face detector --------------------------------------------------
        self.detector = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )

        # Video principale --------------------------------------------------
        self.video_label = QLabel(alignment=Qt.AlignCenter)
        self.video_label.setMinimumSize(640, 480)
        self.video_label.setObjectName("video_label")

        # Nome webcam principale --------------------------------------------------
        self.cam_name_label = QLabel(f"Webcam attiva: {self.current_cam_name}")
        self.cam_name_label.setAlignment(Qt.AlignCenter)

        # Global sidebar toggle (always visible) --------------------------------------------------
        self.toggle_sidebar_global = QPushButton("Nascondi impostazioni")
        self.toggle_sidebar_global.clicked.connect(self.toggle_sidebar)
        self.toggle_sidebar_global.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        # Timer principale --------------------------------------------------
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.running = False
        self.prev_time = time.time()
        self.fps = 0

        # Extra webcam --------------------------------------------------
        self.extra_caps = []
        self.extra_cam_widgets = []
        self.extra_timer = QTimer()
        self.extra_timer.timeout.connect(self.update_extra_cams)
        self.extra_timer.start(200)

        # Layout impostazioni --------------------------------------------------
        settings_layout = QVBoxLayout()
        settings_layout.addWidget(self.create_webcam_group())
        settings_layout.addWidget(self.create_face_group())
        settings_layout.addWidget(self.create_feedback_group())
        settings_layout.addWidget(self.create_extra_cams_group())
        settings_layout.addStretch()

        # Widget saving --------------------------------------------------
        self.settings_widget = QWidget()
        self.settings_widget.setLayout(settings_layout)
        self.settings_widget.setFixedWidth(320)

        # Layout video principale --------------------------------------------------
        video_layout = QVBoxLayout()

        # Top bar with global toggle and camera name
        top_bar = QHBoxLayout()
        top_bar.addWidget(self.toggle_sidebar_global)
        top_bar.addWidget(self.cam_name_label)
        top_bar.addStretch()
        video_layout.addLayout(top_bar)

        video_layout.addWidget(self.video_label)

        # Layout principale --------------------------------------------------
        self.main_layout = QHBoxLayout(self)
        self.main_layout.addWidget(self.settings_widget)
        self.main_layout.addLayout(video_layout)

    # ===================================================================================================================
    # SCANSIONE WEBCAM
    # ===================================================================================================================

    def scan_webcams(self):
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

    # ===================================================================================================================
    # UI SECTIONS
    # ===================================================================================================================

    def create_webcam_group(self):
        group = QGroupBox("Webcam")
        layout = QVBoxLayout()

        self.cam_selector = QComboBox()
        for name in self.available_names:
            self.cam_selector.addItem(name)
        self.cam_selector.currentIndexChanged.connect(self.change_camera)
        layout.addWidget(self.cam_selector)

        self.start_button = QPushButton("Start Camera")
        self.start_button.clicked.connect(self.toggle_camera)
        self.start_button.setStyleSheet("background-color: green; color: white;")
        layout.addWidget(self.start_button)

        self.record_button = QPushButton("Start Recording")
        self.record_button.clicked.connect(self.toggle_recording)
        self.record_button.setStyleSheet("background-color: #173c68; color: white;")
        layout.addWidget(self.record_button)


    # (in-sidebar toggle removed; global toggle remains visible) --------------------------------------------------

        group.setLayout(layout)
        return group
    
    # ===================================================================================================================
    # FACE DETECTION SETTINGS
    # ===================================================================================================================

    def create_face_group(self):
        group = QGroupBox("Rilevamento Volti")
        layout = QVBoxLayout()

        self.color_button = QPushButton("Colore rettangolo")
        self.color_button.clicked.connect(self.choose_color)
        layout.addWidget(self.color_button)

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
    
    # ===================================================================================================================
    # FEEDBACK SETTINGS
    # ===================================================================================================================

    def create_feedback_group(self):
        group = QGroupBox("Feedback")
        layout = QVBoxLayout()

        self.coords_check = QCheckBox("Mostra coordinate")
        self.coords_check.toggled.connect(self.toggle_coords)
        layout.addWidget(self.coords_check)

        self.fps_check = QCheckBox("Mostra FPS")
        self.fps_check.setChecked(self.show_fps)
        self.fps_check.toggled.connect(self.toggle_fps)
        layout.addWidget(self.fps_check)

        self.snapshot_button = QPushButton("Salva snapshot")
        self.snapshot_button.clicked.connect(self.save_snapshot)
        layout.addWidget(self.snapshot_button)

        group.setLayout(layout)
        return group
    
    # ===================================================================================================================
    # EXTRA CAMERAS GROUP
    # ===================================================================================================================

    def create_extra_cams_group(self):
        group = QGroupBox("Altre Webcam")
        layout = QVBoxLayout()

        for cap in self.extra_caps:
            if cap.isOpened():
                cap.release()
        self.extra_caps.clear()
        self.extra_cam_widgets.clear()

        for idx, name in zip(self.available_indices, self.available_names):
            if idx == self.current_cam_index:
                continue

            cap = cv2.VideoCapture(idx, cv2.CAP_MSMF)
            if not cap.isOpened():
                cap.release()
                continue

            self.extra_caps.append(cap)

            name_label = QLabel(name)
            name_label.setAlignment(Qt.AlignCenter)

            video_label = QLabel()
            video_label.setFixedSize(220, 140)
            video_label.setStyleSheet("border: 1px solid #4C566A; background-color: #1E222D;")

            self.extra_cam_widgets.append((name_label, video_label))

            layout.addWidget(name_label)
            layout.addWidget(video_label)

        if not self.extra_cam_widgets:
            layout.addWidget(QLabel("Nessun'altra webcam trovata."))

        group.setLayout(layout)
        self.extra_cams_group = group
        return group

    # ===================================================================================================================
    # ACTIONS
    # ===================================================================================================================

    def toggle_sidebar(self):
        if self.settings_widget.isVisible():
            self.settings_widget.hide()
            if hasattr(self, "toggle_sidebar_button"):
                self.toggle_sidebar_button.setText("Mostra impostazioni")
            if hasattr(self, "toggle_sidebar_global"):
                self.toggle_sidebar_global.setText("Mostra impostazioni")
        else:
            self.settings_widget.show()
            if hasattr(self, "toggle_sidebar_button"):
                self.toggle_sidebar_button.setText("Nascondi impostazioni")
            if hasattr(self, "toggle_sidebar_global"):
                self.toggle_sidebar_global.setText("Nascondi impostazioni")

    def change_camera(self, combo_index):
        if combo_index < 0 or combo_index >= len(self.available_indices):
            return

        new_index = self.available_indices[combo_index]
        new_name = self.available_names[combo_index]

        if self.running:
            self.timer.stop()

        if self.cap.isOpened():
            self.cap.release()

        self.cap = cv2.VideoCapture(new_index, cv2.CAP_MSMF)
        if not self.cap.isOpened():
            print("Errore: impossibile aprire la webcam selezionata.")
            return

        self.current_cam_index = new_index
        self.current_cam_name = new_name
        self.cam_name_label.setText(f"Webcam attiva: {self.current_cam_name}")

        parent_layout = self.extra_cams_group.parentWidget().layout()
        parent_layout.removeWidget(self.extra_cams_group)
        self.extra_cams_group.deleteLater()
        new_group = self.create_extra_cams_group()
        parent_layout.insertWidget(3, new_group)

        if self.running:
            self.timer.start(30)

    def choose_color(self):
        color = QColorDialog.getColor(self.rect_color, self, "Scegli colore")
        if color.isValid():
            self.rect_color = color

    def update_thickness(self, value):
        self.rect_thickness = value

    def update_zoom(self, value):
        self.zoom_factor = value / 100.0

    def toggle_coords(self, checked: bool):
        self.show_coords = checked

    def toggle_fps(self, checked: bool):
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

    # ===================================================================================================================
    # RECORDING
    # ===================================================================================================================

    def toggle_recording(self):
        if not self.running:
            print("La camera deve essere attiva per registrare.")
            return

        if self.recording:
            self.recording = False
            self.record_button.setText("Start Recording")
            self.record_button.setStyleSheet("background-color: #173c68; color: white;")
            if self.video_writer:
                self.video_writer.release()
        else:
            filename = datetime.datetime.now().strftime("record_%Y%m%d_%H%M%S.mp4")
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            self.video_writer = cv2.VideoWriter(filename, fourcc, 30, (w, h))

            self.recording = True
            self.record_start_time = time.time()
            self.record_button.setText("Stop Recording")
            self.record_button.setStyleSheet("background-color: red; color: white;")

    # ===================================================================================================================
    # FRAME UPDATE MAIN
    # ===================================================================================================================

    def update_frame(self):
        ret, frame = self.cap.read()
        if not ret:
            return

        frame = cv2.flip(frame, 1)

        # Zoom digitale --------------------------------------------------
        if self.zoom_factor > 1.0:
            h, w = frame.shape[:2]
            new_w = int(w / self.zoom_factor)
            new_h = int(h / self.zoom_factor)
            x1 = (w - new_w) // 2
            y1 = (h - new_h) // 2
            frame = frame[y1:y1 + new_h, x1:x1 + new_w]
            frame = cv2.resize(frame, (w, h), interpolation=cv2.INTER_LINEAR)

        # FPS --------------------------------------------------
        now = time.time()
        self.fps = 1.0 / max(now - self.prev_time, 0.0001)
        self.prev_time = now

        # Face detection --------------------------------------------------
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.detector.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=6)

        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x + w, y + h),
                          (self.rect_color.blue(), self.rect_color.green(), self.rect_color.red()),
                          self.rect_thickness)
            if self.show_coords:
                cv2.putText(frame, f"{x},{y}", (x, y - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        if self.show_fps:
            cv2.putText(frame, f"FPS: {int(self.fps)}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)

        date_str = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        cv2.putText(frame, date_str, (frame.shape[1] - 260, frame.shape[0] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 2)

        if self.recording:
            elapsed = int(time.time() - self.record_start_time)
            timer_str = time.strftime("%H:%M:%S", time.gmtime(elapsed))

            cv2.circle(frame, (20, 60), 10, (0, 0, 255), -1)
            cv2.putText(frame, "REC", (40, 65),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            cv2.putText(frame, timer_str, (100, 65),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

            if self.video_writer:
                self.video_writer.write(frame)

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        img = QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888)

        pixmap = QPixmap.fromImage(img).scaled(
            self.video_label.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        self.video_label.setPixmap(pixmap)

    # ===================================================================================================================
    # FRAME UPDATE EXTRA CAMS
    # ===================================================================================================================

    def update_extra_cams(self):
        for (name_label, video_label), cap in zip(self.extra_cam_widgets, self.extra_caps):
            if not cap.isOpened():
                continue
            ret, frame = cap.read()
            if not ret:
                continue
            frame = cv2.flip(frame, 1)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb.shape
            img = QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888)
            pixmap = QPixmap

    # ===================================================================================================================
    # SNAPSHOT
    # ===================================================================================================================

    def save_snapshot(self):
        ret, frame = self.cap.read()
        if not ret:
            return
        frame = cv2.flip(frame, 1)
        name = datetime.datetime.now().strftime("snapshot_%Y%m%d_%H%M%S.png")
        cv2.imwrite(name, frame)
        print(f"Snapshot salvato: {name}")

    # ===================================================================================================================
    # CLEAN EXIT
    # ===================================================================================================================

    def closeEvent(self, event):
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


if __name__ == "__main__":
    app = QApplication(sys.argv)

    try:
        with open("style.qss", "r") as f:
            app.setStyleSheet(f.read())
    except FileNotFoundError:
        pass

    window = FaceApp()
    window.show()

    try:
        sys.exit(app.exec())
    except KeyboardInterrupt:
        window.close()
        sys.exit(0)