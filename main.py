import sys
import cv2
import time
import datetime

from PySide6.QtWidgets import (
    QApplication, QLabel, QPushButton, QVBoxLayout, QWidget,
    QHBoxLayout, QGroupBox, QColorDialog, QCheckBox, QSlider
)
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QImage, QPixmap, QColor


class FaceApp(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("APPLICAZIONE DI ACCESSO BIOMETRICO")
        self.resize(1000, 540)
        self.setMinimumSize(800, 450)

        # Parametri
        self.rect_color = QColor(0, 255, 0)
        self.rect_thickness = 2
        self.show_coords = False
        self.show_fps = True

        # Webcam
        self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not self.cap.isOpened():
            raise RuntimeError("Errore: impossibile aprire la webcam.")

        self.detector = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )

        # Video label
        self.video_label = QLabel(alignment=Qt.AlignCenter)
        self.video_label.setMinimumSize(640, 480)
        self.video_label.setObjectName("video_label")

        # Timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.running = False
        self.prev_time = time.time()
        self.fps = 0

        # Layout impostazioni
        settings_layout = QVBoxLayout()
        settings_layout.addWidget(self.create_webcam_group())
        settings_layout.addWidget(self.create_face_group())
        settings_layout.addWidget(self.create_feedback_group())
        settings_layout.addStretch()

        settings_widget = QWidget()
        settings_widget.setLayout(settings_layout)
        settings_widget.setFixedWidth(300)

        main_layout = QHBoxLayout(self)
        main_layout.addWidget(settings_widget)
        main_layout.addWidget(self.video_label, stretch=1)

    # ---------------- UI SECTIONS ----------------
    def create_webcam_group(self):
        group = QGroupBox("Webcam")
        layout = QVBoxLayout()

        self.start_button = QPushButton("Start Camera")
        self.start_button.clicked.connect(self.toggle_camera)
        self.start_button.setStyleSheet("background-color: green; color: white;")
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
        self.thickness_slider = QSlider(Qt.Horizontal)
        self.thickness_slider.setRange(1, 10)
        self.thickness_slider.setValue(self.rect_thickness)
        self.thickness_slider.setTickPosition(QSlider.TicksBelow)
        self.thickness_slider.setTickInterval(1)
        self.thickness_slider.valueChanged.connect(self.update_thickness)
        layout.addWidget(self.thickness_slider)

        group.setLayout(layout)
        return group

    def create_feedback_group(self):
        group = QGroupBox("Feedback")
        layout = QVBoxLayout()

        self.coords_check = QCheckBox("Mostra coordinate")
        self.coords_check.setChecked(self.show_coords)
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

    # ---------------- ACTIONS ----------------
    def choose_color(self):
        color = QColorDialog.getColor(self.rect_color, self, "Scegli colore")
        if color.isValid():
            self.rect_color = color

    def update_thickness(self, value):
        self.rect_thickness = value

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

    # ---------------- FRAME UPDATE ----------------
    def update_frame(self):
        ret, frame = self.cap.read()
        if not ret:
            return

        frame = cv2.flip(frame, 1)

        now = time.time()
        self.fps = 1.0 / max(now - self.prev_time, 0.0001)
        self.prev_time = now

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        faces = self.detector.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=6)

        for (x, y, w, h) in faces:
            cv2.rectangle(
                frame,
                (x, y), (x + w, y + h),
                (self.rect_color.blue(), self.rect_color.green(), self.rect_color.red()),
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

    # ---------------- SNAPSHOT ----------------
    def save_snapshot(self):
        ret, frame = self.cap.read()
        if not ret:
            return
        frame = cv2.flip(frame, 1)
        name = datetime.datetime.now().strftime("snapshot_%Y%m%d_%H%M%S.png")
        cv2.imwrite(name, frame)
        print(f"Snapshot salvato: {name}")

    # ---------------- CLEAN EXIT ----------------
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