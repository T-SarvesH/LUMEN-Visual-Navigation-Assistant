import tensorflow as tf
import numpy as np
import cv2
from tensorflow.keras.models import load_model
from .config import ROUTER_MODEL_PATH, ROUTER_THRESHOLD, IMG_SIZE, TORCH_DEVICE
import os

class RouterModel:
    def __init__(self):
        print(f"🔹 Loading EfficientNet Router model from: {ROUTER_MODEL_PATH}")
        self.model = load_model(ROUTER_MODEL_PATH, compile=False)
        self.labels = ["Animal", "Environmental_Hazard", "Pedestrian", "Vehicle"]
        print("✅ Router model loaded successfully!")

    def center_crop_resize(self, image, target_size=300):
        h, w, _ = image.shape
        min_dim = min(h, w)
        
        # Calculate crop coordinates
        start_x = (w - min_dim) // 2
        start_y = (h - min_dim) // 2
        
        # Crop to a square region (center)
        cropped = image[start_y:start_y + min_dim, start_x:start_x + min_dim]
        
        # Resize to match EfficientNet input
        resized = cv2.resize(cropped, (target_size, target_size))
        
        return resized

    def preprocess(self, frame):
        """Center Resizing and normalize frame for EfficientNet."""
        img = self.center_crop_resize(frame, IMG_SIZE)
        img = img.astype("float32") / 255.0
        return np.expand_dims(img, axis=0)

    def predict(self, frame):
        """
        Returns dictionary of probabilities per class and 
        active classes above threshold.
        """
        preprocessed = self.preprocess(frame)
        preds = self.model.predict(preprocessed, verbose=0)[0]

        result = {label: float(prob) for label, prob in zip(self.labels, preds)}
        active = [lbl for lbl, prob in result.items() if prob >= ROUTER_THRESHOLD]

        return {
            "probabilities": result,
            "active_classes": active
        }

# Example standalone test
# if __name__ == "__main__":
#     router = RouterModel()
#     test_img_path = os.path.join(
#         os.path.dirname(__file__),
#         "TestImageRouter2.jpg"
#     )
#     img = cv2.imread(test_img_path)
#     out = router.predict(img)
#     print(out)
