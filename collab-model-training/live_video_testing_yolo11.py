import cv2
from ultralytics import YOLO

# Load your trained YOLO model
model = YOLO("yolo11m_results/coco_exp/weights/best.pt")  # path to your trained weights

# Open webcam (0 = default camera, change if multiple cams)
cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # Run YOLO inference
    results = model.predict(frame, conf=0.25, imgsz=640, verbose=False)

    # Draw boxes and labels on frame
    annotated_frame = results[0].plot()

    # Show the frame
    cv2.imshow("YOLO Live Detection", annotated_frame)

    # Press 'q' to exit
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()