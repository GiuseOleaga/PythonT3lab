import sys
import cv2
import time
import datetime

from PySide6.QtWidgets import (
    QApplication, QLabel, QPushButton, QVBoxLayout, QWidget,
    QHBoxLayout, QGroupBox, QColorDialog, QCheckBox
)
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QImage, QPixmap, QColor


class FaceApp(QWidget):
    def __init__(self):
        super().__init__()

        # ---------------- WINDOW ----------------
        self.setWindowTitle("APPLICAZIONE DI ACCESSO BIOMETRICO")
        self.resize(1000, 540)
        self.setMinimumSize(800, 450)

        # ---------------- PARAMETERS ----------------
        self.rect_color = QColor(0, 255, 0)
        self.rect_thickness = 2
        self.show_coords = False
        self.show_fps = True

        # ---------------- WEBCAM ----------------
        self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not self.cap.isOpened():
            raise RuntimeError("Errore: impossibile aprire la webcam.")

        # Rilevazione più fluida: mantieni FPS camera reale
        self.camera_fps = self.cap.get(cv2.CAP_PROP_FPS)
        if not self.camera_fps or self.camera_fps <= 0:
            self.camera_fps = 30  # fallback

        self.timer_interval = int(1000.0 / self.camera_fps)

        self.detector = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )

        # ---------------- VIDEO LABEL ----------------
        self.video_label = QLabel(alignment=Qt.AlignCenter)
        self.video_label.setMinimumSize(640, 480)
        self.video_label.setObjectName("video_label")

        # ---------------- TIMER / FPS ----------------
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.running = False
        self.prev_time = time.time()
        self.fps = 0

        # ---------------- SETTINGS PANEL ----------------
        settings_layout = QVBoxLayout()
        settings_layout.addWidget(self.create_webcam_group())
        settings_layout.addWidget(self.create_face_group())
        settings_layout.addWidget(self.create_feedback_group())
        settings_layout.addStretch()

        settings_widget = QWidget()
        settings_widget.setLayout(settings_layout)
        settings_widget.setFixedWidth(300)

        # ---------------- MAIN LAYOUT ----------------
        main_layout = QHBoxLayout(self)
        main_layout.addWidget(settings_widget)
        main_layout.addWidget(self.video_label, stretch=1)

    # ==================================================
    # UI SECTIONS
    # ==================================================
    def create_webcam_group(self):
        group = QGroupBox("Webcam")
        layout = QVBoxLayout()

        self.start_button = QPushButton("Start Camera")
        self.start_button.setCheckable(True)  # per cambiare colore con :checked
        self.start_button.setObjectName("start_button")
        self.start_button.clicked.connect(self.toggle_camera)
        layout.addWidget(self.start_button)

        group.setLayout(layout)
        return group

    def create_face_group(self):
        group = QGroupBox("Rilevamento Volti")
        layout = QVBoxLayout()

        self.color_button = QPushButton("Colore rettangolo")
        self.color_button.clicked.connect(self.choose_color)
        layout.addWidget(self.color_button)

        layout.addWidget(QLabel("Spessore rettangolo"))
        self.thickness_spin = QCheckBox()  # rimane solo lo spessore come slider se vuoi
        layout.addWidget(self.thickness_spin)

        group.setLayout(layout)
        return group

    def create_feedback_group(self):
        group = QGroupBox("Feedback")
        layout = QVBoxLayout()

        self.coords_check = QCheckBox("Mostra coordinate")
        self.coords_check.stateChanged.connect(
            lambda s: setattr(self, "show_coords", s == Qt.Checked)
        )
        layout.addWidget(self.coords_check)

        self.fps_check = QCheckBox("Mostra FPS")
        self.fps_check.setChecked(self.show_fps)
        self.fps_check.stateChanged.connect(
            lambda s: setattr(self, "show_fps", s == Qt.Checked)
        )
        layout.addWidget(self.fps_check)

        self.snapshot_button = QPushButton("Salva snapshot")
        self.snapshot_button.clicked.connect(self.save_snapshot)
        layout.addWidget(self.snapshot_button)

        group.setLayout(layout)
        return group

    # ==================================================
    # ACTIONS
    # ==================================================
    def choose_color(self):
        color = QColorDialog.getColor(self.rect_color, self, "Scegli colore")
        if color.isValid():
            self.rect_color = color

    def toggle_camera(self):
        if self.running:
            self.timer.stop()
            self.video_label.clear()  # disattiva visivamente la camera
        else:
            self.timer.start(self.timer_interval)
        self.running = not self.running

    # ==================================================
    # FRAME UPDATE
    # ==================================================
    def update_frame(self):
        ret, frame = self.cap.read()
        if not ret:
            return

        frame = cv2.flip(frame, 1)

        now = time.time()
        self.fps = 1.0 / max(now - self.prev_time, 0.0001)
        self.prev_time = now

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        faces = self.detector.detectMultiScale(
            gray,
            scaleFactor=1.2,
            minNeighbors=6
        )

        for (x, y, w, h) in faces:
            cv2.rectangle(
                frame,
                (x, y), (x + w, y + h),
                (self.rect_color.blue(),
                 self.rect_color.green(),
                 self.rect_color.red()),
                self.rect_thickness
            )

            if self.show_coords:
                cv2.putText(
                    frame, f"{x},{y}",
                    (x, y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5, (255, 255, 255), 1
                )

        if self.show_fps:
            cv2.putText(
                frame, f"FPS: {int(self.fps)}",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                1, (0, 255, 255), 2
            )

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        img = QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888)

        pixmap = QPixmap.fromImage(img).scaled(
            self.video_label.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        self.video_label.setPixmap(pixmap)

    # ==================================================
    # SNAPSHOT
    # ==================================================
    def save_snapshot(self):
        ret, frame = self.cap.read()
        if not ret:
            return

        frame = cv2.flip(frame, 1)
        name = datetime.datetime.now().strftime("snapshot_%Y%m%d_%H%M%S.png")
        cv2.imwrite(name, frame)
        print(f"Snapshot salvato: {name}")

    # ==================================================
    # CLEAN EXIT
    # ==================================================
    def closeEvent(self, event):
        if self.timer.isActive():
            self.timer.stop()
        if self.cap.isOpened():
            self.cap.release()
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
