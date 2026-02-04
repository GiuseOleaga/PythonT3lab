import sys
import cv2
from PySide6.QtWidgets import (
    QApplication, QLabel, QPushButton, QVBoxLayout, QWidget, QHBoxLayout, 
    QGroupBox, QColorDialog
)
from PySide6.QtCore import QTimer
from PySide6.QtGui import QImage, QPixmap, QColor

class FaceApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Face Detection App")
        self.setFixedSize(900, 520)  # dimensione finestra fissa

        # Colore del rettangolo (default verde)
        self.rect_color = QColor(0, 255, 0)

        # --- Video Label ---
        self.video_label = QLabel()
        self.video_label.setFixedSize(640, 480)
        self.video_label.setStyleSheet("border: 2px solid #555;")

        # --- Pulsanti ---
        self.start_button = QPushButton("Start Camera")
        self.start_button.clicked.connect(self.toggle_camera)

        self.color_button = QPushButton("Cambia Colore Rettangolo")
        self.color_button.clicked.connect(self.choose_color)

        # --- Layout impostazioni ---
        settings_group = QGroupBox("Impostazioni")
        settings_layout = QVBoxLayout()
        settings_layout.addWidget(self.start_button)
        settings_layout.addWidget(self.color_button)
        settings_layout.addStretch()
        settings_group.setLayout(settings_layout)
        settings_group.setFixedWidth(220)

        # --- Layout principale ---
        main_layout = QHBoxLayout()
        main_layout.addWidget(settings_group)
        main_layout.addWidget(self.video_label)
        self.setLayout(main_layout)

        # --- OpenCV e timer ---
        self.cap = cv2.VideoCapture(0)
        self.detector = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.running = False

        # --- Stile globale ---
        self.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-size: 14px;
                padding: 6px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #aaa;
                border-radius: 5px;
                margin-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 3px;
            }
        """)

    def toggle_camera(self):
        if self.running:
            self.timer.stop()
            self.start_button.setText("Start Camera")
        else:
            self.timer.start(30)  # 30 ms ~ 33 fps
            self.start_button.setText("Stop Camera")
        self.running = not self.running

    def choose_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.rect_color = color

    def update_frame(self):
        ret, frame = self.cap.read()
        if not ret:
            return

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.detector.detectMultiScale(gray, 1.3, 5)
        for (x, y, w, h) in faces:
            # Usa il colore scelto
            cv2.rectangle(
                frame, (x, y), (x + w, y + h),
                (self.rect_color.blue(), self.rect_color.green(), self.rect_color.red()), 2
            )

        rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        qt_image = QImage(rgb_image.data, w, h, ch * w, QImage.Format_RGB888)
        self.video_label.setPixmap(QPixmap.fromImage(qt_image))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FaceApp()
    window.show()
    sys.exit(app.exec())
