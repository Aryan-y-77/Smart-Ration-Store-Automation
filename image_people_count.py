import cv2
import numpy as np

# Load model
net = cv2.dnn.readNetFromCaffe(
    "MobileNetSSD_deploy.prototxt",
    "MobileNetSSD_deploy.caffemodel"
)

CLASSES = ["background","aeroplane","bicycle","bird","boat",
           "bottle","bus","car","cat","chair","cow","diningtable",
           "dog","horse","motorbike","person","pottedplant","sheep",
           "sofa","train","tvmonitor"]

# Load image
image = cv2.imread("test.jpg")
(h, w) = image.shape[:2]

# Prepare input
blob = cv2.dnn.blobFromImage(cv2.resize(image, (300, 300)),
                             0.007843, (300, 300), 127.5)

net.setInput(blob)
detections = net.forward()

people_count = 0

for i in range(detections.shape[2]):
    confidence = detections[0, 0, i, 2]

    if confidence > 0.5:
        idx = int(detections[0, 0, i, 1])

        if CLASSES[idx] == "person":
            people_count += 1

            box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
            (startX, startY, endX, endY) = box.astype("int")

            cv2.rectangle(image, (startX, startY),
                          (endX, endY), (0, 255, 0), 2)

# Display result
cv2.putText(image, f"People Count: {people_count}",
            (20, 40), cv2.FONT_HERSHEY_SIMPLEX,
            1, (0, 0, 255), 2)

cv2.imshow("Image Detection", image)
cv2.waitKey(0)
cv2.destroyAllWindows()