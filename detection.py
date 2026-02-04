import cv2 as cv

# Funzione helper per usare colori in RGB invece che BGR
def rgb(r, g, b):
    return (b, g, r)  # OpenCV usa BGR

# Carica il classificatore Haar Cascade per il volto
face_cascade = cv.CascadeClassifier(cv.data.haarcascades + 'haarcascade_frontalface_default.xml')

cap = cv.VideoCapture(0)
if not cap.isOpened():
    print("Camera non apribile")
    exit()

while True:
    ret, frame = cap.read()
    if not ret:
        print("non ricevo il segnale")
        break

    # Specchia orizzontalmente
    frame_flipped = cv.flip(frame, 1)

    # Converti in scala di grigi per il rilevamento
    gray = cv.cvtColor(frame_flipped, cv.COLOR_BGR2GRAY)

    # Rileva i volti
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

    # Disegna un rettangolo intorno ai volti rilevati
    for (x, y, w, h) in faces:
        cv.rectangle(frame_flipped, (x, y), (x + w, y + h), rgb(255, 255, 0), 2)  # Giallo in RGB

    cv.imshow('frame', frame_flipped)

    if cv.waitKey(1) == ord('x'):
        break

cap.release()
cv.destroyAllWindows()
