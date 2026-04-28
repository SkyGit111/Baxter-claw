"""FastAPI Bridge Server for Baxter-Claw.

Provides REST API for high-level robot control via action primitives.
"""

import sys
import argparse
from typing import Optional, Dict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from .models import (
    EnableRequest,
    DisableRequest,
    PickRequest,
    PlaceRequest,
    PlaceByNameRequest,
    MoveToRequest,
    HomeRequest,
    GripperRequest,
    StatusResponse,
    PrimitiveResponse,
    ErrorResponse,
    PickByNameRequest,
    LocateObjectRequest,
    DescribeSceneRequest,
    IdentifyObjectsRequest,
    CaptureImageRequest,
    VisionResponse,
    BimanualPickRequest,
    HandoverRequest,
    SynchronizedMoveRequest,
    DualArmResponse,
)
from .arm_manager import ArmManager


# Create FastAPI app
app = FastAPI(
    title="Baxter-Claw Bridge",
    description="Natural language control bridge for Baxter robot",
    version="0.1.0",
)

# Add CORS middleware for web-based clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global arm manager instance
manager: Optional[ArmManager] = None


@app.on_event("startup")
async def startup_event():
    """Initialize robot connection on startup."""
    global manager
    print("Starting Baxter-Claw Bridge Server...")

    # Manager will be initialized with config in main()
    if manager is None:
        manager = ArmManager()

    # Auto-connect to robot
    manager.connect()
    print("Bridge server ready")


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up on shutdown."""
    global manager
    print("Shutting down Baxter-Claw Bridge Server...")
    if manager:
        manager.disconnect()


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Baxter-Claw Bridge",
        "version": "0.1.0",
        "status": "running"
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    if manager is None:
        raise HTTPException(status_code=503, detail="Manager not initialized")

    status = manager.get_status()
    return {
        "healthy": status['connected'],
        "connected": status['connected'],
        "enabled": status['enabled']
    }


@app.post("/enable")
async def enable():
    """Enable robot motors."""
    if manager is None:
        raise HTTPException(status_code=503, detail="Manager not initialized")

    success = manager.enable()
    if not success:
        raise HTTPException(status_code=500, detail="Failed to enable robot")

    return {"success": True, "message": "Robot enabled"}


@app.post("/disable")
async def disable():
    """Disable robot motors."""
    if manager is None:
        raise HTTPException(status_code=503, detail="Manager not initialized")

    success = manager.disable()
    return {"success": success, "message": "Robot disabled"}


@app.get("/status")
async def status(arm: str = "right") -> StatusResponse:
    """Get robot status."""
    if manager is None:
        raise HTTPException(status_code=503, detail="Manager not initialized")

    return StatusResponse(**manager.get_status(arm))


@app.post("/primitives/pick")
async def pick(req: PickRequest) -> PrimitiveResponse:
    """Execute pick primitive.

    Picks up an object at the specified position.
    """
    if manager is None:
        raise HTTPException(status_code=503, detail="Manager not initialized")

    try:
        result = manager.primitives.pick(
            arm=req.arm,
            position=req.position,
            approach_height=req.approach_height or 0.1
        )

        if not result['success']:
            raise HTTPException(status_code=400, detail=result.get('message', 'Pick failed'))

        return PrimitiveResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Pick failed: {str(e)}")


@app.post("/primitives/place")
async def place(req: PlaceRequest) -> PrimitiveResponse:
    """Execute place primitive.

    Places the held object at the specified position.
    """
    if manager is None:
        raise HTTPException(status_code=503, detail="Manager not initialized")

    try:
        result = manager.primitives.place(
            arm=req.arm,
            position=req.position,
            approach_height=req.approach_height or 0.1
        )

        if not result['success']:
            raise HTTPException(status_code=400, detail=result.get('message', 'Place failed'))

        return PrimitiveResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Place failed: {str(e)}")


@app.post("/primitives/place_by_name")
async def place_by_name(req: PlaceByNameRequest) -> PrimitiveResponse:
    """Execute place_by_name primitive.

    Places the held object relative to another object using vision.
    """
    if manager is None:
        raise HTTPException(status_code=503, detail="Manager not initialized")

    try:
        result = await manager.primitives.place_by_name(
            arm=req.arm,
            target_object_name=req.target_object_name,
            relative_position=req.relative_position,
            approach_height=req.approach_height or 0.1
        )

        if not result['success']:
            raise HTTPException(status_code=400, detail=result.get('message', 'PlaceByName failed'))

        return PrimitiveResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"PlaceByName failed: {str(e)}")


@app.post("/primitives/move_to")
async def move_to(req: MoveToRequest) -> PrimitiveResponse:
    """Execute move_to primitive.

    Moves end-effector to specified pose.
    """
    if manager is None:
        raise HTTPException(status_code=503, detail="Manager not initialized")

    try:
        result = manager.primitives.move_to(
            arm=req.arm,
            position=req.position,
            orientation=req.orientation
        )

        if not result['success']:
            raise HTTPException(status_code=400, detail=result.get('message', 'Move failed'))

        return PrimitiveResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Move failed: {str(e)}")


@app.post("/primitives/home")
async def home(req: HomeRequest) -> PrimitiveResponse:
    """Execute home primitive.

    Returns arm to home position.
    """
    if manager is None:
        raise HTTPException(status_code=503, detail="Manager not initialized")

    try:
        result = manager.primitives.home(arm=req.arm)

        if not result['success']:
            raise HTTPException(status_code=400, detail=result.get('message', 'Home failed'))

        return PrimitiveResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Home failed: {str(e)}")


@app.post("/gripper")
async def gripper(req: GripperRequest):
    """Control gripper."""
    if manager is None:
        raise HTTPException(status_code=503, detail="Manager not initialized")

    success = manager.driver.gripper_command(
        arm=req.arm,
        action=req.action,
        force=req.force or 30.0
    )

    if not success:
        raise HTTPException(status_code=400, detail="Gripper command failed")

    return {"success": True, "message": f"Gripper {req.action} executed"}


@app.post("/stop")
async def stop(arm: str = "right"):
    """Stop arm motion (emergency stop)."""
    if manager is None:
        raise HTTPException(status_code=503, detail="Manager not initialized")

    success = manager.emergency_stop()
    return {"success": success, "message": "Emergency stop executed"}


@app.get("/camera")
async def camera(camera: str = "right_hand"):
    """Capture image from camera."""
    if manager is None:
        raise HTTPException(status_code=503, detail="Manager not initialized")

    try:
        import base64
        import cv2

        # Handle D455 depth camera separately
        if camera == "d455":
            rgb_image, depth_image = manager.driver.capture_rgbd()

            if rgb_image is None:
                return {
                    "success": False,
                    "message": "D455 camera not available or failed to capture",
                    "camera": camera
                }

            # Encode RGB image as JPEG
            success, jpeg_buffer = cv2.imencode('.jpg', rgb_image, [cv2.IMWRITE_JPEG_QUALITY, 90])
            if not success:
                return {
                    "success": False,
                    "message": "Failed to encode D455 image",
                    "camera": camera
                }

            image_bytes = jpeg_buffer.tobytes()
            image_b64 = base64.b64encode(image_bytes).decode('utf-8')

            return {
                "success": True,
                "message": f"Image captured from {camera}",
                "camera": camera,
                "image": image_b64,
                "size": len(image_bytes)
            }

        # Capture image from Baxter cameras
        image_bytes = manager.driver.capture_image(camera)

        if not image_bytes:
            return {
                "success": False,
                "message": "Failed to capture image",
                "camera": camera
            }

        # Encode as base64 for JSON response
        image_b64 = base64.b64encode(image_bytes).decode('utf-8')

        return {
            "success": True,
            "message": f"Image captured from {camera}",
            "camera": camera,
            "image": image_b64,
            "size": len(image_bytes)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Camera capture failed: {str(e)}")


# Vision endpoints

@app.post("/vision/pick_by_name")
async def pick_by_name(req: PickByNameRequest) -> VisionResponse:
    """Pick object by name using vision.

    Uses VLM to locate the object in camera image, then executes pick.
    """
    if manager is None:
        raise HTTPException(status_code=503, detail="Manager not initialized")

    if not manager.vlm_client:
        raise HTTPException(status_code=400, detail="VLM client not configured")

    try:
        result = await manager.primitives.pick_by_name(
            req.arm,
            req.object_name,
            req.use_d455,
            req.approach_height or 0.1
        )

        if not result['success']:
            raise HTTPException(status_code=400, detail=result.get('message', 'Vision pick failed'))

        return VisionResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Vision pick failed: {str(e)}")


@app.post("/vision/locate_object")
async def locate_object(req: LocateObjectRequest) -> VisionResponse:
    """Locate object using vision without moving robot."""
    if manager is None:
        raise HTTPException(status_code=503, detail="Manager not initialized")

    if not manager.vlm_client:
        raise HTTPException(status_code=400, detail="VLM client not configured")

    result = await manager.primitives.locate_object(
        req.object_name,
        req.use_d455
    )

    return VisionResponse(**result)


@app.post("/vision/describe_scene")
async def describe_scene(req: DescribeSceneRequest) -> VisionResponse:
    """Get description of current scene."""
    if manager is None:
        raise HTTPException(status_code=503, detail="Manager not initialized")

    if not manager.vlm_client:
        raise HTTPException(status_code=400, detail="VLM client not configured")

    result = await manager.primitives.describe_scene(req.use_d455, req.language)

    return VisionResponse(**result)


@app.post("/vision/identify_objects")
async def identify_objects(req: IdentifyObjectsRequest) -> VisionResponse:
    """Identify all objects in scene."""
    if manager is None:
        raise HTTPException(status_code=503, detail="Manager not initialized")

    if not manager.vlm_client:
        raise HTTPException(status_code=400, detail="VLM client not configured")

    result = await manager.primitives.identify_objects(req.use_d455)

    return VisionResponse(**result)


@app.post("/vision/locate_multiview")
async def locate_multiview(req: LocateObjectRequest) -> VisionResponse:
    """Locate object using multi-view VLM approach.

    Uses D455 + head camera for initial detection, then optionally
    uses wrist camera for close-up refinement.
    """
    if manager is None:
        raise HTTPException(status_code=503, detail="Manager not initialized")

    if not manager.vlm_client:
        raise HTTPException(status_code=400, detail="VLM client not configured")

    try:
        result = await manager.primitives.locate_object_multiview(
            object_name=req.object_name,
            arm=req.arm or "right",
            use_wrist_refinement=True
        )

        if not result['success']:
            raise HTTPException(status_code=400, detail=result.get('message', 'Multi-view localization failed'))

        return VisionResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Multi-view localization error: {str(e)}")


# Dual-arm coordination endpoints

@app.post("/dualarm/bimanual_pick")
async def bimanual_pick(req: BimanualPickRequest) -> DualArmResponse:
    """Pick object with both arms simultaneously.

    Useful for large or heavy objects that require two hands.
    """
    if manager is None:
        raise HTTPException(status_code=503, detail="Manager not initialized")

    try:
        result = manager.primitives.bimanual_pick(
            req.object_position,
            req.left_offset or [-0.05, 0.0, 0.0],
            req.right_offset or [0.05, 0.0, 0.0],
            req.approach_height or 0.1
        )

        if not result['success']:
            raise HTTPException(status_code=400, detail=result.get('message', 'Bimanual pick failed'))

        return DualArmResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Bimanual pick failed: {str(e)}")


@app.post("/dualarm/handover")
async def handover(req: HandoverRequest) -> DualArmResponse:
    """Handover object from one arm to another."""
    if manager is None:
        raise HTTPException(status_code=503, detail="Manager not initialized")

    try:
        result = manager.primitives.handover(
            req.from_arm,
            req.to_arm,
            req.handover_position
        )

        if not result['success']:
            raise HTTPException(status_code=400, detail=result.get('message', 'Handover failed'))

        return DualArmResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Handover failed: {str(e)}")


@app.post("/dualarm/synchronized_move")
async def synchronized_move(req: SynchronizedMoveRequest) -> DualArmResponse:
    """Move both arms simultaneously to specified positions."""
    if manager is None:
        raise HTTPException(status_code=503, detail="Manager not initialized")

    try:
        result = manager.primitives.synchronized_move(
            req.left_position,
            req.right_position,
            req.left_orientation,
            req.right_orientation
        )

        if not result['success']:
            raise HTTPException(status_code=400, detail=result.get('message', 'Synchronized move failed'))

        return DualArmResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Synchronized move failed: {str(e)}")


@app.post("/dualarm/parallel_pick_two")
async def parallel_pick_two(req: Dict) -> DualArmResponse:
    """Pick two different objects simultaneously with both arms.

    This provides TRUE physical parallelism - both arms move at the same time.
    """
    if manager is None:
        raise HTTPException(status_code=503, detail="Manager not initialized")

    try:
        left_object = req.get('left_object_name')
        right_object = req.get('right_object_name')

        if not left_object or not right_object:
            raise HTTPException(status_code=400, detail="Missing left_object_name or right_object_name")

        result = await manager.primitives.parallel_pick_two_objects(
            left_object_name=left_object,
            right_object_name=right_object,
            approach_height=req.get('approach_height', 0.1),
            speed=req.get('speed', 0.3)
        )

        if not result['success']:
            raise HTTPException(status_code=400, detail=result.get('message', 'Parallel pick failed'))

        return DualArmResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Parallel pick failed: {str(e)}")


@app.post("/dualarm/parallel_place_two")
async def parallel_place_two(req: Dict) -> DualArmResponse:
    """Place two held objects simultaneously to different targets.

    This provides TRUE physical parallelism - both arms move at the same time.
    """
    if manager is None:
        raise HTTPException(status_code=503, detail="Manager not initialized")

    try:
        left_target = req.get('left_target_name')
        left_position = req.get('left_relative_position', 'on_top')
        right_target = req.get('right_target_name')
        right_position = req.get('right_relative_position', 'on_top')

        if not left_target or not right_target:
            raise HTTPException(status_code=400, detail="Missing target names")

        result = await manager.primitives.parallel_place_two_objects(
            left_target_name=left_target,
            left_relative_position=left_position,
            right_target_name=right_target,
            right_relative_position=right_position,
            approach_height=req.get('approach_height', 0.1),
            speed=req.get('speed', 0.3)
        )

        if not result['success']:
            raise HTTPException(status_code=400, detail=result.get('message', 'Parallel place failed'))

        return DualArmResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Parallel place failed: {str(e)}")


def main():
    """Main entry point for bridge server."""
    parser = argparse.ArgumentParser(description="Baxter-Claw Bridge Server")
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to configuration YAML file"
    )
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Host to bind to (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8420,
        help="Port to bind to (default: 8420)"
    )
    parser.add_argument(
        "--enable-grasp-verification",
        action="store_true",
        default=None,
        help="Enable post-grasp verification with wrist camera (overrides config file)"
    )
    parser.add_argument(
        "--grasp-verify-retries",
        type=int,
        default=None,
        help="Maximum retry attempts for failed grasp verification (overrides config file)"
    )

    args = parser.parse_args()

    # Initialize global manager with config
    global manager
    manager = ArmManager(
        config_path=args.config,
        enable_grasp_verification=args.enable_grasp_verification if args.enable_grasp_verification else None,
        grasp_verify_retries=args.grasp_verify_retries
    )

    # Start server
    print(f"Starting server on {args.host}:{args.port}")
    if args.enable_grasp_verification:
        print(f"[Experimental] Grasp verification enabled (max retries: {args.grasp_verify_retries})")
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
