import { accelerometer, gyroscope, setUpdateIntervalForType, SensorTypes } from 'react-native-sensors';

// Fill in your private IP + port
const WEBSOCKET_URL = 'ws://<Your-Private-IP>/Lumen-ws';

class VioService {
  constructor() {
    this.ws = null;
    this.accelSubscription = null;
    this.gyroSubscription = null;
    this.sensorBuffer = [];
    this.BATCH_SIZE = 5;
    this.fps = 30;
    this.lastSentTime = 0;
    this.alpha = 0.8;
    this.lastFiltered = { x: 0, y: 0, z: 0 };
    this.currentFrameBytes = null; // latest camera raw bytes
    this.frameWidth = 0;
    this.frameHeight = 0;
  }

  connect(onServerMessage) {
    this.ws = new WebSocket(WEBSOCKET_URL);

    this.ws.onopen = () => {
      console.log('VioService: WebSocket Connected');
      this.startStreaming();
    };

    this.ws.onclose = () => console.log('VioService: WebSocket Disconnected');

    this.ws.onerror = (error) => {
      console.error('VioService: WebSocket Error', error);
      onServerMessage('Connection Error');
    };

    this.ws.onmessage = (event) => onServerMessage(event.data);
  }

  lowPassFilter(value, axis) {
    const filtered = this.alpha * this.lastFiltered[axis] + (1 - this.alpha) * value;
    this.lastFiltered[axis] = filtered;
    return filtered;
  }

  updateCameraFrame(bytes, width, height) {
    if (!bytes) return;
    this.currentFrameBytes = bytes;
    this.frameWidth = width;
    this.frameHeight = height;
  }

  startStreaming() {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return;

    const minInterval = 1000 / this.fps;
    setUpdateIntervalForType(SensorTypes.accelerometer, minInterval);
    setUpdateIntervalForType(SensorTypes.gyroscope, minInterval);

    const bufferAndSend = (data) => {
      const now = Date.now();
      if (now - this.lastSentTime >= minInterval) {
        this.lastSentTime = now;

        data.x = this.lowPassFilter(data.x, 'x');
        data.y = this.lowPassFilter(data.y, 'y');
        data.z = this.lowPassFilter(data.z, 'z');

        this.sensorBuffer.push(data);

        if (this.sensorBuffer.length >= this.BATCH_SIZE || this.currentFrameBytes) {
          const dataPacket = {
            imu_readings: this.sensorBuffer,
            frame: this.currentFrameBytes ? Array.from(this.currentFrameBytes) : null,
            frame_width: this.frameWidth,
            frame_height: this.frameHeight
          };

          if (this.ws.readyState === WebSocket.OPEN) {
            try {
              this.ws.send(JSON.stringify(dataPacket));
              console.log(
                `VioService: Sent ${this.sensorBuffer.length} IMU readings + ${this.currentFrameBytes ? '1 frame' : '0 frames'}`
              );
            } catch (err) {
              console.error('VioService: send error', err);
            }
          }

          this.sensorBuffer = [];
          this.currentFrameBytes = null;
        }
      }
    };

    this.accelSubscription = accelerometer.subscribe(
      ({ x, y, z, timestamp }) => bufferAndSend({ type: 'accel', x, y, z, timestamp })
    );

    this.gyroSubscription = gyroscope.subscribe(
      ({ x, y, z, timestamp }) => bufferAndSend({ type: 'gyro', x, y, z, timestamp })
    );

    console.log(`VioService: IMU + Frame streaming started at ~${this.fps} FPS.`);
  }

  disconnect() {
    if (this.accelSubscription) this.accelSubscription.unsubscribe();
    if (this.gyroSubscription) this.gyroSubscription.unsubscribe();
    if (this.ws) this.ws.close();
    console.log('VioService: Cleaned up resources.');
  }
}

export const vioService = new VioService();
