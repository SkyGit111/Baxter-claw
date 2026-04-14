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
    arm: Literal["left", "right"] = Field(default="right", description="Which arm to use")
    object_name: str = Field(..., description="Name of object to pick (e.g., 'red cup')")
    camera: str = Field(default="right_hand", description="Camera to use for vision")
    approach_height: Optional[float] = Field(default=0.1, description="Height offset for pre-grasp pose")


class LocateObjectRequest(BaseModel):
    """Request to locate object using vision."""
    object_name: str = Field(..., description="Name of object to locate")
    camera: str = Field(default="right_hand", description="Camera to use for vision")


class DescribeSceneRequest(BaseModel):
    """Request to describe the scene."""
    camera: str = Field(default="right_hand", description="Camera to use for vision")


class IdentifyObjectsRequest(BaseModel):
    """Request to identify all objects in scene."""
    camera: str = Field(default="right_hand", description="Camera to use for vision")


class CaptureImageRequest(BaseModel):
    """Request to capture image from camera."""
    camera: str = Field(default="right_hand", description="Camera to use")


class VisionResponse(BaseModel):
    """Response from vision operations."""
    success: bool
    message: str
    object_name: Optional[str] = None
    position: Optional[List[float]] = None
    confidence: Optional[float] = None
    description: Optional[str] = None
    bounding_box: Optional[List[int]] = None
    objects: Optional[List[Dict]] = None


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


