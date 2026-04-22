"""Collision detection for robot arm motion.

This module provides collision detection by monitoring arm position during motion.
If the arm position remains unchanged for a specified duration, it indicates
a potential collision with an obstacle.

This is an experimental feature designed to be fully decoupled from core functionality.
"""

import time
import threading
from typing import Dict, List, Optional, Callable
import numpy as np


class CollisionDetector:
    """Detects collisions by monitoring arm position stagnation during motion.

    Detection logic:
    1. Periodically sample arm position during motion
    2. If position change is below threshold for consecutive samples, mark as stagnant
    3. If stagnation duration exceeds threshold, trigger collision detection
    4. Stop motion and return collision signal

    This detector is designed to be:
    - Decoupled: Can be disabled without affecting core functionality
    - Safe: Conservative thresholds to avoid false positives
    - Non-intrusive: Runs in background thread
    """

    def __init__(
        self,
        enabled: bool = False,
        position_threshold: float = 0.005,  # 5mm - position change threshold
        stagnation_duration: float = 2.0,   # 2 seconds - time before collision detected
        sample_interval: float = 0.2,       # 200ms - sampling frequency
        min_samples: int = 3,               # Minimum consecutive stagnant samples
        debug: bool = False
    ):
        """Initialize collision detector.

        Args:
            enabled: Enable collision detection (default: False for safety)
            position_threshold: Minimum position change (meters) to consider as movement
            stagnation_duration: Time (seconds) of stagnation before collision detected
            sample_interval: Time (seconds) between position samples
            min_samples: Minimum consecutive stagnant samples before triggering
            debug: Enable debug logging
        """
        self.enabled = enabled
        self.position_threshold = position_threshold
        self.stagnation_duration = stagnation_duration
        self.sample_interval = sample_interval
        self.min_samples = min_samples
        self.debug = debug

        # Internal state
        self._monitoring = False
        self._collision_detected = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        if self.enabled:
            print(f"[CollisionDetector] Enabled (threshold={position_threshold}m, "
                  f"duration={stagnation_duration}s, interval={sample_interval}s)")
        else:
            print("[CollisionDetector] Disabled")

    def start_monitoring(
        self,
        arm: str,
        get_position_func: Callable[[], Optional[List[float]]],
        on_collision: Optional[Callable[[], None]] = None
    ) -> bool:
        """Start monitoring arm position for collision detection.

        Args:
            arm: Arm identifier ('left' or 'right')
            get_position_func: Function to get current arm position [x, y, z]
            on_collision: Optional callback function when collision detected

        Returns:
            True if monitoring started, False if disabled or already monitoring
        """
        if not self.enabled:
            return False

        if self._monitoring:
            if self.debug:
                print(f"[CollisionDetector] Already monitoring {arm}")
            return False

        # Reset state
        self._collision_detected = False
        self._stop_event.clear()

        # Start monitoring thread
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            args=(arm, get_position_func, on_collision),
            daemon=True
        )
        self._monitoring = True
        self._monitor_thread.start()

        if self.debug:
            print(f"[CollisionDetector] Started monitoring {arm}")

        return True

    def stop_monitoring(self) -> Dict:
        """Stop monitoring and return detection results.

        Returns:
            Dict with 'collision_detected' (bool) and 'message' (str)
        """
        # Capture collision state before stopping
        collision_state = self._collision_detected

        if not self._monitoring:
            # Thread may have already stopped due to collision detection
            # Return the collision state
            return {
                'collision_detected': collision_state,
                'message': 'Collision detected' if collision_state else 'Monitoring already stopped'
            }

        # Signal thread to stop
        self._stop_event.set()

        # Wait for thread to finish (with timeout)
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=1.0)

        self._monitoring = False

        result = {
            'collision_detected': self._collision_detected,
            'message': 'Collision detected' if self._collision_detected else 'No collision'
        }

        if self.debug:
            print(f"[CollisionDetector] Stopped monitoring: {result['message']}")

        return result

    def is_monitoring(self) -> bool:
        """Check if currently monitoring."""
        return self._monitoring

    def collision_detected(self) -> bool:
        """Check if collision was detected."""
        return self._collision_detected

    def _monitor_loop(
        self,
        arm: str,
        get_position_func: Callable[[], Optional[List[float]]],
        on_collision: Optional[Callable[[], None]]
    ):
        """Main monitoring loop (runs in background thread).

        Args:
            arm: Arm identifier
            get_position_func: Function to get current position
            on_collision: Callback when collision detected
        """
        try:
            previous_position = None
            stagnant_count = 0
            stagnation_start_time = None

            while not self._stop_event.is_set():
                # Get current position
                current_position = get_position_func()

                if current_position is None:
                    if self.debug:
                        print(f"[CollisionDetector] Warning: Could not get position for {arm}")
                    time.sleep(self.sample_interval)
                    continue

                # First sample - just record position
                if previous_position is None:
                    previous_position = current_position
                    if self.debug:
                        print(f"[CollisionDetector] Initial position: {current_position}")
                    time.sleep(self.sample_interval)
                    continue

                # Calculate position change
                position_change = self._calculate_distance(previous_position, current_position)

                if self.debug:
                    print(f"[CollisionDetector] {arm} position change: {position_change:.6f}m "
                          f"(threshold: {self.position_threshold:.6f}m)")

                # Check if position is stagnant
                if position_change < self.position_threshold:
                    # Start timing stagnation on first stagnant sample
                    if stagnation_start_time is None:
                        stagnation_start_time = time.time()
                        if self.debug:
                            print(f"[CollisionDetector] Stagnation started")

                    stagnant_count += 1

                    # Check if stagnation duration exceeded
                    stagnation_time = time.time() - stagnation_start_time

                    if self.debug:
                        print(f"[CollisionDetector] Stagnant count: {stagnant_count}/{self.min_samples}, "
                              f"duration: {stagnation_time:.2f}/{self.stagnation_duration:.2f}s")

                    if stagnant_count >= self.min_samples and stagnation_time >= self.stagnation_duration:
                        # Collision detected!
                        self._collision_detected = True

                        print(f"[CollisionDetector] ⚠ COLLISION DETECTED on {arm}!")
                        print(f"  Position stagnant for {stagnation_time:.2f}s")
                        print(f"  Position: {current_position}")

                        # Trigger callback
                        if on_collision:
                            try:
                                on_collision()
                            except Exception as e:
                                print(f"[CollisionDetector] Error in collision callback: {e}")

                        # Stop monitoring
                        break
                else:
                    # Position changed - reset stagnation tracking
                    if stagnant_count > 0 and self.debug:
                        print(f"[CollisionDetector] Position changed, resetting stagnation tracking")
                    stagnant_count = 0
                    stagnation_start_time = None

                # Update previous position
                previous_position = current_position

                # Wait before next sample
                time.sleep(self.sample_interval)

        except Exception as e:
            print(f"[CollisionDetector] Error in monitoring loop: {e}")
            import traceback
            traceback.print_exc()

        finally:
            self._monitoring = False
            if self.debug:
                print(f"[CollisionDetector] Monitoring loop ended")

    def _calculate_distance(self, pos1: List[float], pos2: List[float]) -> float:
        """Calculate Euclidean distance between two positions.

        Args:
            pos1: First position [x, y, z]
            pos2: Second position [x, y, z]

        Returns:
            Distance in meters
        """
        # Handle different position formats (may include orientation)
        p1 = np.array(pos1[:3])  # Take only x, y, z
        p2 = np.array(pos2[:3])

        return float(np.linalg.norm(p1 - p2))

    def enable(self):
        """Enable collision detection."""
        self.enabled = True
        print("[CollisionDetector] Enabled")

    def disable(self):
        """Disable collision detection."""
        self.enabled = False
        if self._monitoring:
            self.stop_monitoring()
        print("[CollisionDetector] Disabled")

    def get_config(self) -> Dict:
        """Get current configuration.

        Returns:
            Dict with current settings
        """
        return {
            'enabled': self.enabled,
            'position_threshold': self.position_threshold,
            'stagnation_duration': self.stagnation_duration,
            'sample_interval': self.sample_interval,
            'min_samples': self.min_samples,
            'debug': self.debug
        }

    def update_config(self, **kwargs):
        """Update configuration parameters.

        Args:
            **kwargs: Configuration parameters to update
        """
        if 'enabled' in kwargs:
            self.enabled = kwargs['enabled']
        if 'position_threshold' in kwargs:
            self.position_threshold = kwargs['position_threshold']
        if 'stagnation_duration' in kwargs:
            self.stagnation_duration = kwargs['stagnation_duration']
        if 'sample_interval' in kwargs:
            self.sample_interval = kwargs['sample_interval']
        if 'min_samples' in kwargs:
            self.min_samples = kwargs['min_samples']
        if 'debug' in kwargs:
            self.debug = kwargs['debug']

        print(f"[CollisionDetector] Configuration updated: {self.get_config()}")
