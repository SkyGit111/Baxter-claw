/**
 * HTTP client for communicating with Baxter-Claw bridge server.
 */

import axios, { AxiosInstance } from 'axios';

export interface BridgeConfig {
  url: string;
  timeout?: number;
}

export class BridgeClient {
  private client: AxiosInstance;

  constructor(config: BridgeConfig) {
    this.client = axios.create({
      baseURL: config.url,
      timeout: config.timeout || 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });
  }

  async enable(): Promise<any> {
    const response = await this.client.post('/enable');
    return response.data;
  }

  async disable(): Promise<any> {
    const response = await this.client.post('/disable');
    return response.data;
  }

  async getStatus(arm: string = 'right'): Promise<any> {
    const response = await this.client.get('/status', {
      params: { arm },
    });
    return response.data;
  }

  async pick(arm: string, position: number[], approachHeight?: number): Promise<any> {
    const response = await this.client.post('/primitives/pick', {
      arm,
      position,
      approach_height: approachHeight,
    });
    return response.data;
  }

  async place(arm: string, position: number[], approachHeight?: number): Promise<any> {
    const response = await this.client.post('/primitives/place', {
      arm,
      position,
      approach_height: approachHeight,
    });
    return response.data;
  }

  async moveTo(arm: string, position: number[], orientation?: number[]): Promise<any> {
    const response = await this.client.post('/primitives/move_to', {
      arm,
      position,
      orientation,
    });
    return response.data;
  }

  async home(arm: string): Promise<any> {
    const response = await this.client.post('/primitives/home', {
      arm,
    });
    return response.data;
  }

  async gripperControl(arm: string, action: string, force?: number): Promise<any> {
    const response = await this.client.post('/gripper', {
      arm,
      action,
      force,
    });
    return response.data;
  }

  async emergencyStop(): Promise<any> {
    const response = await this.client.post('/stop');
    return response.data;
  }

  async health(): Promise<any> {
    const response = await this.client.get('/health');
    return response.data;
  }

  // Vision methods

  async pickByName(arm: string, objectName: string, camera?: string): Promise<any> {
    const response = await this.client.post('/vision/pick_by_name', {
      arm,
      object_name: objectName,
      camera: camera || 'right_hand',
    });
    return response.data;
  }

  async locateObject(objectName: string, camera?: string): Promise<any> {
    const response = await this.client.post('/vision/locate_object', {
      object_name: objectName,
      camera: camera || 'right_hand',
    });
    return response.data;
  }

  async describeScene(camera?: string): Promise<any> {
    const response = await this.client.post('/vision/describe_scene', {
      camera: camera || 'right_hand',
    });
    return response.data;
  }

  async identifyObjects(camera?: string): Promise<any> {
    const response = await this.client.post('/vision/identify_objects', {
      camera: camera || 'right_hand',
    });
    return response.data;
  }

  async captureImage(camera?: string): Promise<any> {
    const response = await this.client.get('/camera', {
      params: { camera: camera || 'right_hand' },
    });
    return response.data;
  }
}
