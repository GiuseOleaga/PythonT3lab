import sys
import cv2
from PySide6.QtWidgets import (
    QApplication, QLabel, QPushButton, QVBoxLayout, QWidget, QHBoxLayout,
    QGroupBox, QColorDialog, QSpinBox, QCheckBox, QComboBox
)
from PySide6.QtCore import QTimer
from PySide6.QtGui import QImage, QPixmap, QColor
import datetime


class FaceApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Face Detection App")
        self.setFixedSize(1000, 540)

        # --- Parametri ---
        self.rect_color = QColor(0, 255, 0)
        self.rect_thickness = 2
        self.min_face_size = 50
        self.show_coords = False

        # Webcam
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            raise RuntimeError("Errore: impossibile aprire la webcam.")

        # Haar Cascade
        self.detector = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )

        # Video label
        self.video_label = QLabel()
        self.video_label.setFixedSize(640, 480)
        self.video_label.setStyleSheet("border: 2px solid #555;")

        # Timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.running = False

        # Layout impostazioni
        settings_layout = QVBoxLayout()
        settings_layout.addWidget(self.create_webcam_group())
        settings_layout.addWidget(self.create_face_group())
        settings_layout.addWidget(self.create_feedback_group())
        settings_layout.addStretch()

        settings_group = QWidget()
        settings_group.setLayout(settings_layout)
        settings_group.setFixedWidth(300)

        # Layout principale
        main_layout = QHBoxLayout()
        main_layout.addWidget(settings_group)
        main_layout.addWidget(self.video_label)
        self.setLayout(main_layout)

        # Stile
        self.setStyleSheet("""
            QPushButton { background-color: #4CAF50; color: white; font-size: 14px; padding: 6px; border-radius: 5px; }
            QPushButton:hover { background-color: #45a049; }
            QGroupBox { font-weight: bold; border: 1px solid #aaa; border-radius: 5px; margin-top: 10px; }
            QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top center; padding: 0 3px; }
            QSpinBox { width: 60px; }
        """)

    # -------------------------- CREATE SECTIONS --------------------------
    def create_webcam_group(self):
        group = QGroupBox("Webcam")
        layout = QVBoxLayout()

        self.start_button = QPushButton("Start Camera")
        self.start_button.clicked.connect(self.toggle_camera)
        layout.addWidget(self.start_button)

        layout.addWidget(QLabel("Risoluzione:"))
        self.res_combo = QComboBox()
        self.res_combo.addItems(["640x480", "800x600", "1280x720"])
        self.res_combo.currentTextChanged.connect(self.change_resolution)
        layout.addWidget(self.res_combo)

        group.setLayout(layout)
        return group

    def create_face_group(self):
        group = QGroupBox("Rilevamento Volti")
        layout = QVBoxLayout()

        self.color_button = QPushButton("Cambia Colore Rettangolo")
        self.color_button.clicked.connect(self.choose_color)
        layout.addWidget(self.color_button)

        layout.addWidget(QLabel("Spessore rettangolo:"))
        self.thickness_spin = QSpinBox()
        self.thickness_spin.setValue(self.rect_thickness)
        self.thickness_spin.setRange(1, 10)
        self.thickness_spin.valueChanged.connect(self.update_thickness)
        layout.addWidget(self.thickness_spin)

        layout.addWidget(QLabel("Dimensione minima volto:"))
        self.min_face_spin = QSpinBox()
        self.min_face_spin.setValue(self.min_face_size)
        self.min_face_spin.setRange(20, 500)
        self.min_face_spin.valueChanged.connect(self.update_min_face)
        layout.addWidget(self.min_face_spin)

        group.setLayout(layout)
        return group

    def create_feedback_group(self):
        group = QGroupBox("Feedback")
        layout = QVBoxLayout()

        self.coords_check = QCheckBox("Mostra coordinate volti")
        self.coords_check.stateChanged.connect(self.toggle_coords)
        layout.addWidget(self.coords_check)

        self.snapshot_button = QPushButton("Salva Snapshot")
        self.snapshot_button.clicked.connect(self.save_snapshot)
        layout.addWidget(self.snapshot_button)

        group.setLayout(layout)
        return group

    # -------------------------- CAMERA --------------------------
    def toggle_camera(self):
        if self.running:
            self.timer.stop()
            self.start_button.setText("Start Camera")
        else:
            self.timer.start(30)
            self.start_button.setText("Stop Camera")
        self.running = not self.running

    def change_resolution(self, text):
        w, h = map(int, text.split("x"))
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, w)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, h)

    # -------------------------- SETTINGS --------------------------
    def choose_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.rect_color = color

    def update_thickness(self, value):
        self.rect_thickness = value

    def update_min_face(self, value):
        self.min_face_size = value

    def toggle_coords(self, state):
        self.show_coords = state == 2

    # -------------------------- FRAME UPDATE --------------------------
    def update_frame(self):
        ret, frame = self.cap.read()
        if not ret:
            return

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        faces = self.detector.detectMultiScale(
            gray,
            scaleFactor=1.2,
            minNeighbors=6,
            minSize=(self.min_face_size, self.min_face_size)
        )

        for (x, y, w, h) in faces:
            cv2.rectangle(
                frame, (x, y), (x + w, y + h),
                (self.rect_color.blue(), self.rect_color.green(), self.rect_color.red()),
                self.rect_thickness
            )

            if self.show_coords:
                cv2.putText(frame, f"({x},{y})", (x, y - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        qt_img = QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888)
        self.video_label.setPixmap(QPixmap.fromImage(qt_img))

    # -------------------------- SNAPSHOT --------------------------
    def save_snapshot(self):
        ret, frame = self.cap.read()
        if not ret:
            return
        filename = datetime.datetime.now().strftime("snapshot_%Y%m%d_%H%M%S.png")
        cv2.imwrite(filename, frame)
        print(f"Snapshot salvato: {filename}")

    # -------------------------- CLEAN EXIT --------------------------
    def closeEvent(self, event):
        if self.cap.isOpened():
            self.cap.release()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FaceApp()
    window.show()
    sys.exit(app.exec())