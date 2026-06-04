"""Pydantic data models for API requests and responses."""

from typing import Dict, List, Optional, Literal
from pydantic import BaseModel, Field


class EnableRequest(BaseModel):
    """Request to enable the robot."""
    pass


class DisableRequest(BaseModel):
    """Request to disable the robot."""
    pass


class PickRequest(BaseModel):
    """Request to execute pick primitive."""
    arm: Literal["left", "right"] = Field(default="right", description="Which arm to use")
    position: List[float] = Field(..., description="Target position [x, y, z] in meters")
    approach_height: Optional[float] = Field(
        default=0.1, description="Height offset for pre-grasp pose"
    )


class PlaceRequest(BaseModel):
    """Request to execute place primitive."""
    arm: Literal["left", "right"] = Field(default="right", description="Which arm to use")
    position: List[float] = Field(..., description="Target position [x, y, z] in meters")
    approach_height: Optional[float] = Field(
        default=0.1, description="Height offset for pre-place pose"
    )


class PlaceByNameRequest(BaseModel):
    """Request to place object relative to another object using vision."""
    arm: Literal["left", "right"] = Field(default="right", description="Which arm to use")
    target_object_name: str = Field(..., description="Name of reference object (e.g., 'yellow block')")
    relative_position: str = Field(
        default="next_to",
        description="Where to place: 'next_to', 'on_top', 'behind', 'in_front'"
    )
    approach_height: Optional[float] = Field(
        default=0.1, description="Height offset for pre-place pose"
    )


class MoveToRequest(BaseModel):
    """Request to move end-effector to specified pose."""
    arm: Literal["left", "right"] = Field(default="right", description="Which arm to use")
    position: List[float] = Field(..., description="Target position [x, y, z] in meters")
    orientation: Optional[List[float]] = Field(
        default=None, description="Target orientation [roll, pitch, yaw] in radians"
    )


class HomeRequest(BaseModel):
    """Request to return arm to home position."""
    arm: Literal["left", "right", "both"] = Field(default="right", description="Which arm(s) to use")


class GripperRequest(BaseModel):
    """Request to control gripper."""
    arm: Literal["left", "right"] = Field(default="right", description="Which arm to use")
    action: Literal["open", "close", "calibrate"] = Field(..., description="Gripper action")
    force: Optional[float] = Field(default=30.0, description="Grip force (0-100)")


class MoveJointsRequest(BaseModel):
    """Request for low-level joint space motion (reserved for future use)."""
    arm: Literal["left", "right"] = Field(default="right", description="Which arm to use")
    positions: Dict[str, float] = Field(..., description="Joint positions in radians")
    speed: Optional[float] = Field(default=0.3, description="Motion speed (0-1)")


class StatusResponse(BaseModel):
    """Robot status response."""
    connected: bool
    enabled: bool
    arm: str
    joint_angles: Dict[str, float]
    endpoint_pose: List[float]  # [x, y, z, roll, pitch, yaw]
    gripper_position: float
    gripper_force: float


class PrimitiveResponse(BaseModel):
    """Response from primitive execution."""
    success: bool
    message: str
    arm: Optional[str] = None
    final_position: Optional[List[float]] = None


class ErrorResponse(BaseModel):
    """Error response."""
    success: bool = False
    error: str
    details: Optional[str] = None


# Vision-related models

class PickByNameRequest(BaseModel):
    """Request to pick object by name using vision."""
    arm: Literal["left", "right", "auto"] = Field(default="auto", description="Which arm to use ('auto' for automatic selection)")
    object_name: str = Field(..., description="Name of object to pick (e.g., 'red cup')")
    use_d455: bool = Field(default=True, description="Use D455 depth camera (recommended)")
    approach_height: Optional[float] = Field(default=0.1, description="Height offset for pre-grasp pose")


class LocateObjectRequest(BaseModel):
    """Request to locate object using vision."""
    object_name: str = Field(..., description="Name of object to locate")
    use_d455: bool = Field(default=True, description="Use D455 depth camera (recommended)")
    arm: Optional[str] = Field(default="right", description="Which arm to use for multi-view (left/right)")


class DescribeSceneRequest(BaseModel):
    """Request to describe the scene."""
    use_d455: bool = Field(default=True, description="Use D455 depth camera (recommended)")
    language: str = Field(default="zh", description="Response language (zh/en)")


class IdentifyObjectsRequest(BaseModel):
    """Request to identify all objects in scene."""
    use_d455: bool = Field(default=True, description="Use D455 depth camera (recommended)")


class CaptureImageRequest(BaseModel):
    """Request to capture image from camera."""
    camera: str = Field(default="right_hand", description="Camera to use")


class VisionResponse(BaseModel):
    """Response from vision operations."""
    success: bool
    message: str
    arm: Optional[str] = None  # Which arm was used (for pick operations)
    found: Optional[bool] = None  # Whether object was found
    object_name: Optional[str] = None
    position: Optional[List[float]] = None
    confidence: Optional[float] = None
    description: Optional[str] = None
    bounding_box: Optional[List[int]] = None
    objects: Optional[List[Dict]] = None
    multi_view_validated: Optional[bool] = None  # Multi-view validation status
    wrist_validated: Optional[bool] = None  # Wrist camera validation status


# Dual-arm coordination models

class BimanualPickRequest(BaseModel):
    """Request to pick object with both arms."""
    object_position: List[float] = Field(..., description="Center position of object [x, y, z]")
    left_offset: Optional[List[float]] = Field(
        default=[-0.05, 0.0, 0.0],
        description="Offset for left gripper from center"
    )
    right_offset: Optional[List[float]] = Field(
        default=[0.05, 0.0, 0.0],
        description="Offset for right gripper from center"
    )
    approach_height: Optional[float] = Field(default=0.1, description="Height offset for pre-grasp")


class HandoverRequest(BaseModel):
    """Request to handover object between arms."""
    from_arm: Literal["left", "right"] = Field(..., description="Arm currently holding object")
    to_arm: Literal["left", "right"] = Field(..., description="Arm to receive object")
    handover_position: Optional[List[float]] = Field(
        default=None,
        description="Optional handover position [x, y, z], auto-calculated if None"
    )


class SynchronizedMoveRequest(BaseModel):
    """Request to move both arms simultaneously."""
    left_position: List[float] = Field(..., description="Target position for left arm [x, y, z]")
    right_position: List[float] = Field(..., description="Target position for right arm [x, y, z]")
    left_orientation: Optional[List[float]] = Field(
        default=None,
        description="Optional orientation for left arm [roll, pitch, yaw]"
    )
    right_orientation: Optional[List[float]] = Field(
        default=None,
        description="Optional orientation for right arm [roll, pitch, yaw]"
    )


class DualArmResponse(BaseModel):
    """Response from dual-arm operations."""
    success: bool
    message: str
    left_position: Optional[List[float]] = None
    right_position: Optional[List[float]] = None
    handover_position: Optional[List[float]] = None


class BimanualHoldAndRotateRequest(BaseModel):
    """Request to hold one ruler segment fixed while rotating another segment around their hinge."""
    fixed_arm: Literal["left", "right"] = Field(
        default="left",
        description="Arm that holds the fixed segment"
    )
    moving_arm: Literal["left", "right"] = Field(
        default="right",
        description="Arm that rotates the moving segment"
    )
    fixed_segment_color: str = Field(
        ...,
        description="Color of the segment to be held fixed (e.g., 'blue', 'yellow', 'green')"
    )
    moving_segment_color: str = Field(
        ...,
        description="Color of the segment to be rotated (e.g., 'blue', 'yellow', 'green')"
    )
    fixed_grasp_name: Optional[str] = Field(
        default=None,
        description="Optional specific description of fixed grasp point"
    )
    moving_grasp_name: Optional[str] = Field(
        default=None,
        description="Optional specific description of moving grasp point"
    )
    angle_degrees: float = Field(
        ...,
        description="Rotation angle in degrees (e.g., 30, 60, 90)"
    )
    direction: Literal["clockwise", "counterclockwise"] = Field(
        ...,
        description="Rotation direction: 'clockwise' or 'counterclockwise'"
    )
    segment_length: float = Field(
        default=0.15,
        description="Length of each ruler segment in meters (default 15cm)"
    )
    use_d455: bool = Field(
        default=True,
        description="Use D455 depth camera for localization"
    )
    approach_height: float = Field(
        default=0.10,
        description="Height offset for pre-grasp poses"
    )
    speed: float = Field(
        default=0.10,
        description="Motion speed ratio (0-1), kept low for safety"
    )
    waypoint_angle_step_degrees: float = Field(
        default=10.0,
        description="Angle step between waypoints in degrees"
    )
    keep_z_constant: bool = Field(
        default=True,
        description="Keep Z coordinate constant during rotation (planar motion)"
    )
    dry_run: bool = Field(
        default=False,
        description="If True, only compute and return plan without executing"
    )


class HoldAndRotateResponse(BaseModel):
    """Response from bimanual hold and rotate operation."""
    success: bool
    message: str
    fixed_arm: Optional[str] = None
    moving_arm: Optional[str] = None
    fixed_segment_color: Optional[str] = None
    moving_segment_color: Optional[str] = None
    fixed_grasp_position: Optional[List[float]] = None
    moving_grasp_position: Optional[List[float]] = None
    fixed_segment_midpoint: Optional[List[float]] = None
    moving_segment_midpoint: Optional[List[float]] = None
    hinge_observed_position: Optional[List[float]] = None
    candidate_hinges: Optional[List[List[float]]] = None
    hinge_position: Optional[List[float]] = None
    hinge_selection_reason: Optional[str] = None
    target_position: Optional[List[float]] = None
    waypoints: Optional[List[List[float]]] = None
    angle_degrees: Optional[float] = None
    direction: Optional[str] = None
    failed_stage: Optional[str] = None
    failed_waypoint_index: Optional[int] = None
    warnings: Optional[List[str]] = None
    dry_run: Optional[bool] = None




class BimanualShapeRulerRequest(BaseModel):
    """Request for bimanual shape ruler task (push mode)."""
    fixed_arm: Literal["left", "right"] = Field(
        default="left",
        description="Arm that holds the fixed segment"
    )
    moving_arm: Literal["left", "right"] = Field(
        default="right",
        description="Arm that pushes the moving segment"
    )
    target_shape: Literal["L"] = Field(
        default="L",
        description="Target shape configuration"
    )
    l_shape_blue_turn_direction: Literal["clockwise", "counterclockwise"] = Field(
        default="clockwise",
        description="Blue segment turn direction for L-shape"
    )
    config_path: Optional[str] = Field(
        default="config/ruler_task.yaml",
        description="Path to ruler task configuration file"
    )
    dry_run: bool = Field(
        default=False,
        description="If True, only compute plan without executing"
    )


class ShapeRulerResponse(BaseModel):
    """Response from bimanual shape ruler task."""
    success: bool
    message: str
    
    # Arms and mode
    fixed_arm: Optional[str] = None
    moving_arm: Optional[str] = None
    push_mode: bool = True
    moving_gripper_close: bool = False
    
    # Raw VLM localization results
    raw_red_grasp_position: Optional[List[float]] = None
    raw_blue_push_position: Optional[List[float]] = None
    raw_green_joint_position: Optional[List[float]] = None
    raw_orange_joint_position: Optional[List[float]] = None
    
    # Motion coordinates (XY from raw, Z fixed)
    motion_red_grasp_position: Optional[List[float]] = None
    motion_blue_push_position: Optional[List[float]] = None
    motion_green_joint_position: Optional[List[float]] = None
    motion_orange_joint_position: Optional[List[float]] = None
    motion_z: Optional[float] = None
    approach_z: Optional[float] = None
    
    # Geometry
    L1: Optional[float] = None  # G-O length
    L2: Optional[float] = None  # O-B length
    O_target: Optional[List[float]] = None
    B_target: Optional[List[float]] = None
    target_shape: Optional[str] = None
    red_yellow_target_angle_deg: Optional[float] = None
    blue_yellow_target_angle_deg: Optional[float] = None
    
    # Push configuration
    push_contact_offset_xy: Optional[List[float]] = None
    
    # Waypoints (distinguish model and execution)
    all_model_waypoints: Optional[List[List[float]]] = None
    execution_waypoints: Optional[List[List[float]]] = None
    push_execution_waypoints: Optional[List[List[float]]] = None
    waypoint_yaws: Optional[List[float]] = None
    skip_first_waypoint: Optional[bool] = None
    
    # Joint angle validation
    green_joint_angle_check_results: Optional[List[Dict]] = None
    orange_joint_angle_check_results: Optional[List[Dict]] = None
    joint_limit_violation: Optional[bool] = None
    
    # Pose validation
    pose_validation_results: Optional[List[Dict]] = None
    
    # Execution details
    failed_stage: Optional[str] = None
    failed_waypoint_index: Optional[int] = None
    warnings: Optional[List[str]] = None
    dry_run: Optional[bool] = None


