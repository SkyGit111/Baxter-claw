"""OpenClaw plugin entry point for Baxter-Claw."""

import * as fs from 'fs';
import * as path from 'path';
import { BridgeClient } from './src/bridge-client';

// Load plugin configuration
const configPath = path.join(__dirname, 'openclaw.plugin.json');
const config = JSON.parse(fs.readFileSync(configPath, 'utf-8'));

// Initialize bridge client
const bridgeClient = new BridgeClient({
  url: config.bridge.url,
  timeout: config.bridge.timeout,
});

// Tool implementations
const tools = {
  robot_enable: async (params: any) => {
    try {
      const result = await bridgeClient.enable();
      return {
        success: true,
        message: result.message || 'Robot enabled successfully',
      };
    } catch (error: any) {
      return {
        success: false,
        error: error.message || 'Failed to enable robot',
      };
    }
  },

  robot_disable: async (params: any) => {
    try {
      const result = await bridgeClient.disable();
      return {
        success: true,
        message: result.message || 'Robot disabled successfully',
      };
    } catch (error: any) {
      return {
        success: false,
        error: error.message || 'Failed to disable robot',
      };
    }
  },

  robot_status: async (params: any) => {
    try {
      const arm = params.arm || 'right';
      const status = await bridgeClient.getStatus(arm);
      return {
        success: true,
        data: status,
      };
    } catch (error: any) {
      return {
        success: false,
        error: error.message || 'Failed to get robot status',
      };
    }
  },

  pick: async (params: any) => {
    try {
      const { arm = 'right', position, approach_height } = params;

      if (!position || position.length !== 3) {
        return {
          success: false,
          error: 'Position must be an array of 3 numbers [x, y, z]',
        };
      }

      const result = await bridgeClient.pick(arm, position, approach_height);
      return {
        success: true,
        message: result.message,
        data: result,
      };
    } catch (error: any) {
      return {
        success: false,
        error: error.response?.data?.detail || error.message || 'Pick operation failed',
      };
    }
  },

  place: async (params: any) => {
    try {
      const { arm = 'right', position, approach_height } = params;

      if (!position || position.length !== 3) {
        return {
          success: false,
          error: 'Position must be an array of 3 numbers [x, y, z]',
        };
      }

      const result = await bridgeClient.place(arm, position, approach_height);
      return {
        success: true,
        message: result.message,
        data: result,
      };
    } catch (error: any) {
      return {
        success: false,
        error: error.response?.data?.detail || error.message || 'Place operation failed',
      };
    }
  },

  move_to: async (params: any) => {
    try {
      const { arm = 'right', position, orientation } = params;

      if (!position || position.length !== 3) {
        return {
          success: false,
          error: 'Position must be an array of 3 numbers [x, y, z]',
        };
      }

      if (orientation && orientation.length !== 3) {
        return {
          success: false,
          error: 'Orientation must be an array of 3 numbers [roll, pitch, yaw]',
        };
      }

      const result = await bridgeClient.moveTo(arm, position, orientation);
      return {
        success: true,
        message: result.message,
        data: result,
      };
    } catch (error: any) {
      return {
        success: false,
        error: error.response?.data?.detail || error.message || 'MoveTo operation failed',
      };
    }
  },

  home: async (params: any) => {
    try {
      const { arm = 'right' } = params;
      const result = await bridgeClient.home(arm);
      return {
        success: true,
        message: result.message,
        data: result,
      };
    } catch (error: any) {
      return {
        success: false,
        error: error.response?.data?.detail || error.message || 'Home operation failed',
      };
    }
  },

  gripper_control: async (params: any) => {
    try {
      const { arm = 'right', action, force } = params;

      if (!action) {
        return {
          success: false,
          error: 'Action is required (open, close, or calibrate)',
        };
      }

      const result = await bridgeClient.gripperControl(arm, action, force);
      return {
        success: true,
        message: result.message,
      };
    } catch (error: any) {
      return {
        success: false,
        error: error.response?.data?.detail || error.message || 'Gripper control failed',
      };
    }
  },

  emergency_stop: async (params: any) => {
    try {
      const result = await bridgeClient.emergencyStop();
      return {
        success: true,
        message: 'Emergency stop executed',
      };
    } catch (error: any) {
      return {
        success: false,
        error: error.message || 'Emergency stop failed',
      };
    }
  },

  // Vision tools

  pick_by_name: async (params: any) => {
    try {
      const { arm = 'right', object_name, camera = 'right_hand' } = params;

      if (!object_name) {
        return {
          success: false,
          error: 'object_name is required',
        };
      }

      const result = await bridgeClient.pickByName(arm, object_name, camera);
      return {
        success: true,
        message: result.message,
        data: result,
      };
    } catch (error: any) {
      return {
        success: false,
        error: error.response?.data?.detail || error.message || 'Pick by name failed',
      };
    }
  },

  locate_object: async (params: any) => {
    try {
      const { object_name, camera = 'right_hand' } = params;

      if (!object_name) {
        return {
          success: false,
          error: 'object_name is required',
        };
      }

      const result = await bridgeClient.locateObject(object_name, camera);
      return {
        success: result.success,
        message: result.message,
        data: result,
      };
    } catch (error: any) {
      return {
        success: false,
        error: error.response?.data?.detail || error.message || 'Locate object failed',
      };
    }
  },

  describe_scene: async (params: any) => {
    try {
      const { camera = 'right_hand' } = params;
      const result = await bridgeClient.describeScene(camera);
      return {
        success: true,
        message: 'Scene described',
        description: result.description,
      };
    } catch (error: any) {
      return {
        success: false,
        error: error.response?.data?.detail || error.message || 'Describe scene failed',
      };
    }
  },

  identify_objects: async (params: any) => {
    try {
      const { camera = 'right_hand' } = params;
      const result = await bridgeClient.identifyObjects(camera);
      return {
        success: true,
        message: result.message,
        objects: result.objects,
      };
    } catch (error: any) {
      return {
        success: false,
        error: error.response?.data?.detail || error.message || 'Identify objects failed',
      };
    }
  },
};

// Export plugin interface
export default {
  name: config.name,
  version: config.version,
  description: config.description,
  tools,
};
