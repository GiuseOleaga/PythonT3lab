import sys
import cv2
from PySide6.QtWidgets import QApplication, QLabel, QPushButton, QVBoxLayout, QWidget, QHBoxLayout
from PySide6.QtCore import QTimer
from PySide6.QtGui import QImage, QPixmap

class FaceApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Face Detection App")

        # Video Label
        self.video_label = QLabel()
        self.video_label.setFixedSize(640, 480)

        # Pulsante start/stop
        self.start_button = QPushButton("Start")
        self.start_button.clicked.connect(self.toggle_camera)
        self.running = False

        # Layout
        control_layout = QVBoxLayout()
        control_layout.addWidget(self.start_button)
        control_layout.addStretch()

        main_layout = QHBoxLayout()
        main_layout.addLayout(control_layout)
        main_layout.addWidget(self.video_label)
        self.setLayout(main_layout)

        # Timer per aggiornare i frame
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)

        # OpenCV
        self.cap = cv2.VideoCapture(0)
        self.detector = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

    def toggle_camera(self):
        if self.running:
            self.timer.stop()
            self.start_button.setText("Start")
        else:
            self.timer.start(30)  # aggiornamento ogni 30ms
            self.start_button.setText("Stop")
        self.running = not self.running

    def update_frame(self):
        ret, frame = self.cap.read()
        if not ret:
            return

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.detector.detectMultiScale(gray, 1.3, 5)
        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

        rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        qt_image = QImage(rgb_image.data, w, h, ch * w, QImage.Format_RGB888)
        self.video_label.setPixmap(QPixmap.fromImage(qt_image))

app = QApplication(sys.argv)
window = FaceApp()
window.show()
sys.exit(app.exec())
