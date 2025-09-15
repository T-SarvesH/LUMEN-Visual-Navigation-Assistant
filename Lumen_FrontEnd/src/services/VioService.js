import { accelerometer, gyroscope, setUpdateIntervalForType, SensorTypes } from 'react-native-sensors';

// Note: Fill out the field using ur own home nw priv IP. Later will remain static when we get a static IP / Hosting

const WEBSOCKET_URL = 'ws://<COMP_PRIVATE_IP>/ws/vio';

class VioService {
  constructor() {
    this.ws = null;
    this.accelSubscription = null;
    this.gyroSubscription = null;
    this.sensorBuffer = [];
    this.BATCH_SIZE = 5; // batch IMU readings
    this.fps = 30; // send 30 FPS max
    this.lastSentTime = 0;
    this.alpha = 0.8; // smoothing factor
    this.lastFiltered = { x: 0, y: 0, z: 0 };
  }

  connect(onServerMessage) {
    this.ws = new WebSocket(WEBSOCKET_URL);

    this.ws.onopen = () => console.log('VioService: WebSocket Connected');
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

  startStreaming() {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      console.error('VioService: Cannot start streaming, WebSocket is not open.');
      return;
    }

    const minInterval = 1000 / this.fps; // milliseconds per frame
    setUpdateIntervalForType(SensorTypes.accelerometer, minInterval);
    setUpdateIntervalForType(SensorTypes.gyroscope, minInterval);

    const bufferAndSend = (data) => {
      const now = Date.now();

      if (now - this.lastSentTime >= minInterval) {
        this.lastSentTime = now;

        // Apply low-pass smoothing
        data.x = this.lowPassFilter(data.x, 'x');
        data.y = this.lowPassFilter(data.y, 'y');
        data.z = this.lowPassFilter(data.z, 'z');

        this.sensorBuffer.push(data);

        if (this.sensorBuffer.length >= this.BATCH_SIZE) {
          const dataPacket = {
            imu_readings: this.sensorBuffer,
            frame_data: null, // camera frame will be added later
          };
          if (this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(dataPacket));
          }
          console.log(`VioService: Sent batch of ${this.sensorBuffer.length} readings`);
          this.sensorBuffer = [];
        }
      }
    };

    this.accelSubscription = accelerometer.subscribe(
      ({ x, y, z, timestamp }) => bufferAndSend({ type: 'accel', x, y, z, timestamp })
    );

    this.gyroSubscription = gyroscope.subscribe(
      ({ x, y, z, timestamp }) => bufferAndSend({ type: 'gyro', x, y, z, timestamp })
    );

    console.log(`VioService: IMU streaming started at ~${this.fps} FPS.`);
  }

  disconnect() {
    if (this.accelSubscription) this.accelSubscription.unsubscribe();
    if (this.gyroSubscription) this.gyroSubscription.unsubscribe();
    if (this.ws) this.ws.close();
    console.log('VioService: Cleaned up resources.');
  }
}

export const vioService = new VioService();
