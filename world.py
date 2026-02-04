import cv2 as cv
import sys

img = cv.imread(cv.samples.findFile("starry_night.jpg"), cv.IMREAD_UNCHANGED)

if img is None:
    sys.exit("Could not read the image.")

cv.imshow("Display window", img)

while True:
     if cv.waitKey(1) == ord('x'):
        break

cv.release()
cv.destroyAllWindows()
