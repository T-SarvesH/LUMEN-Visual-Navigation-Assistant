# LUMEN: Visual Navigation Assistant 👁️🔊

LUMEN is a real-time "Vision-to-Voice" neural prosthetic designed to empower the visually impaired. By leveraging computer vision, spatial reasoning, and natural language generation, LUMEN translates a complex visual world into actionable audio descriptions.

---

## Core Features

* **Intelligent Scene Description:** Periodic natural language summaries of the user's surroundings using a refined Scenery Manager (30s window).
* **Real-time Threat Detection:** Immediate identification of spatial obstacles and hazards with low-latency alerts.
* **Dynamic Model Routing:** A custom "Router" that intelligently switches between YOLO models (e.g., Traffic, Indoor, General) based on visual context.
* **Low-Latency WebRTC Streaming:** High-performance React Native frontend delivering a 30 FPS video stream for real-time inference.
* **Accessibility-First UI:** High-contrast, dark-mode interface designed with `NativeWind` and `Lucide` icons.

---

## 🛠 Tech Stack

### Backend (The Brain)
* **FastAPI:** High-performance Python framework for WebSocket and WebRTC management.
* **PyTorch & Ultralytics:** Powering the YOLOv8 inference engine.
* **Aiortc:** Facilitating WebRTC media exchange for low-latency video.
* **NarratorBot:** Custom module for Rule-Based NL + LLM Refinement.

### Frontend (The Interface)
* **React Native:** Cross-platform mobile architecture.
* **Vision Camera:** High-speed camera frame capture and frame processors.
* **NativeWind:** Tailwind CSS styling for mobile.
* **Lucide-Icons & FontAwesome:** High-contrast, accessible iconography.

---

## 🏗 System Architecture

LUMEN operates on a split-inference architecture. The mobile device acts as a sensor hub, streaming data to a GPU-accelerated backend.

1.  **Ingestion:** Mobile app captures video via `react-native-vision-camera`.
2.  **Streaming:** Frames are transmitted over a **WebRTC** PeerConnection.
3.  **Inference Pipeline:**
    * **Router:** Classifies the scene and activates relevant YOLO weights.
    * **YOLO:** Detects specific objects and bounding boxes.
    * **Threat Analyzer:** Calculates spatial proximity and identifies hazards.
4.  **Narration:** `SceneryManager` aggregates data to generate refined scene descriptions.
5.  **Feedback:** The backend pushes metadata via a **DataChannel** for UI updates and audio instructions.

---

## 🚀 Getting Started

### Prerequisites
* Python 3.10+
* Node.js 18+
* Android SDK / ADB
