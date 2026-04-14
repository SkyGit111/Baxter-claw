"""Optimized VLM prompts for different stages of object localization.

This module provides carefully crafted prompts for each stage of the
multi-view localization pipeline, with detailed instructions to maximize
VLM accuracy.
"""

from typing import Dict, Optional, Tuple


class VLMPrompts:
    """Manages VLM prompts for different localization stages."""

    def __init__(self, workspace_bounds: Optional[Dict[str, Tuple[float, float]]] = None):
        """Initialize VLM prompts.

        Args:
            workspace_bounds: Robot workspace bounds {axis: (min, max)}
        """
        self.workspace_bounds = workspace_bounds or {
            'x': [0.3, 0.9],
            'y': [-0.7, 0.7],
            'z': [-0.2, 0.5],
        }

    def get_phase1_d455_prompt(self, object_name: str) -> str:
        """Get prompt for Phase 1 D455 camera analysis.

        This is the primary localization prompt using depth-enhanced RGB.

        Args:
            object_name: Name of object to locate

        Returns:
            Detailed prompt string
        """
        prompt = f"""You are analyzing an image from a robot's overhead depth camera (Intel RealSense D455) to locate a specific object.

**TASK**: Locate the "{object_name}" in this image with high precision.

**CAMERA SETUP**:
- This is a top-down view from a fixed overhead camera
- The camera provides both RGB and depth information
- The workspace (table surface) is clearly visible
- The robot's workspace boundaries are:
  * X-axis (forward/backward): {self.workspace_bounds['x'][0]:.2f}m to {self.workspace_bounds['x'][1]:.2f}m from robot base
  * Y-axis (left/right): {self.workspace_bounds['y'][0]:.2f}m to {self.workspace_bounds['y'][1]:.2f}m from robot base
  * Z-axis (height): {self.workspace_bounds['z'][0]:.2f}m to {self.workspace_bounds['z'][1]:.2f}m above table surface

**YOUR ANALYSIS SHOULD INCLUDE**:

1. **Object Detection** (Critical):
   - Is the "{object_name}" clearly visible in the image? (yes/no)
   - If multiple similar objects exist, identify the most prominent/accessible one
   - Describe the object's appearance (color, shape, size, distinctive features)

2. **Precise Location** (Critical):
   - Provide pixel coordinates of the object's CENTER as a bounding box [x1, y1, x2, y2]
   - x1, y1 = top-left corner of bounding box
   - x2, y2 = bottom-right corner of bounding box
   - Coordinate system: (0, 0) is top-left of image
   - Make the bounding box TIGHT around the object (not too large)

3. **3D Position Estimation**:
   - Estimate the object's 3D position [x, y, z] in meters relative to robot base
   - X: distance forward from robot (positive = forward)
   - Y: distance left/right from robot (negative = right, positive = left)
   - Z: height above table surface (typically 0.0 to 0.2m for objects on table)
   - Use the workspace bounds above as reference

4. **Confidence Assessment**:
   - Rate your confidence in this detection (0-100%)
   - Consider: object clarity, occlusion, lighting, distinctiveness
   - Be honest: lower confidence if uncertain

5. **Contextual Information**:
   - Describe surrounding objects or obstacles
   - Note any occlusions or visibility issues
   - Mention if the object is graspable from this view

**OUTPUT FORMAT** (JSON only, no other text):
```json
{{
    "found": true/false,
    "position": [x, y, z],
    "confidence": 0-100,
    "description": "Detailed description of the object and its location",
    "bounding_box": [x1, y1, x2, y2],
    "surrounding_context": "Description of nearby objects and obstacles",
    "graspability": "Assessment of whether object is graspable"
}}
```

**IMPORTANT GUIDELINES**:
- Be PRECISE with bounding box coordinates - this directly affects grasp accuracy
- If object is partially occluded, still provide best estimate but lower confidence
- If object is not found, set "found": false and explain why in description
- Position estimates should be realistic within the workspace bounds
- Consider object size when estimating Z height (taller objects have higher Z)
"""
        return prompt

    def get_phase1_head_camera_prompt(self, object_name: str) -> str:
        """Get prompt for Phase 1 head camera validation.

        This is a secondary validation prompt from a different angle.

        Args:
            object_name: Name of object to locate

        Returns:
            Validation prompt string
        """
        prompt = f"""You are analyzing an image from a robot's head-mounted camera to VALIDATE object detection.

**TASK**: Confirm the presence and location of "{object_name}" from this secondary viewpoint.

**CAMERA SETUP**:
- This is from the robot's head camera (different angle than primary camera)
- The view may be slightly tilted (not perfectly top-down)
- This image has been cropped to focus on the workspace
- Some parts of the robot arm may be visible

**YOUR VALIDATION SHOULD INCLUDE**:

1. **Object Confirmation**:
   - Can you see the "{object_name}" in this view? (yes/no)
   - Does it match the expected appearance?
   - Is it in a similar location as expected?

2. **Location Verification**:
   - Provide bounding box [x1, y1, x2, y2] for the object
   - Estimate position [x, y, z] relative to robot base
   - Note: This is a validation, so rough estimates are acceptable

3. **Confidence**:
   - How confident are you in this detection? (0-100%)
   - Is the view clear or are there occlusions?

4. **Consistency Check**:
   - Does this view provide any additional information?
   - Are there any discrepancies or concerns?

**OUTPUT FORMAT** (JSON only):
```json
{{
    "found": true/false,
    "position": [x, y, z],
    "confidence": 0-100,
    "description": "Brief description and validation notes",
    "bounding_box": [x1, y1, x2, y2],
    "validation_notes": "Any concerns or additional observations"
}}
```

**IMPORTANT**:
- This is a SECONDARY validation, not primary detection
- Focus on confirming presence rather than precise localization
- If view is unclear, indicate lower confidence
"""
        return prompt

    def get_phase2_wrist_camera_prompt(
        self,
        object_name: str,
        initial_position: list
    ) -> str:
        """Get prompt for Phase 2 wrist camera refinement.

        This is for close-up detailed analysis.

        Args:
            object_name: Name of object to locate
            initial_position: Initial position estimate from Phase 1

        Returns:
            Refinement prompt string
        """
        prompt = f"""You are analyzing a CLOSE-UP image from a robot's wrist-mounted camera for PRECISE object localization.

**TASK**: Refine the location of "{object_name}" using this detailed close-up view.

**CONTEXT**:
- Initial detection estimated object at position: {initial_position}
- The robot has moved its wrist camera close to this location
- This is a close-up view providing much more detail than the overhead view
- The camera is pointing downward at the object

**CAMERA SETUP**:
- Wrist-mounted camera (moves with robot arm)
- Close-up view (typically 20-40cm from object)
- Higher detail and clarity than overhead cameras
- May have slight motion blur or shadows from robot arm

**YOUR REFINEMENT SHOULD INCLUDE**:

1. **Detailed Object Analysis**:
   - Confirm this is the correct "{object_name}"
   - Describe fine details: texture, edges, surface features, markings
   - Note the object's orientation and pose
   - Assess object condition and graspability

2. **Precise Localization**:
   - Provide TIGHT bounding box [x1, y1, x2, y2] around the object
   - The object should be centered or near-center in this view
   - Estimate the object's center position relative to the camera
   - Note: Since camera is close, small pixel errors = large position errors

3. **Grasp Planning Information**:
   - Identify best grasp points (edges, handles, flat surfaces)
   - Note any obstacles or constraints around the object
   - Assess object stability (is it stable or might it tip?)
   - Recommend grasp approach angle if applicable

4. **Refinement Confidence**:
   - Rate confidence in this refined detection (0-100%)
   - This should typically be HIGH (>85%) due to close-up clarity
   - Lower confidence only if object is unclear or unexpected

5. **Comparison with Initial Estimate**:
   - Does the object appear where expected?
   - Any significant differences from initial estimate?
   - Suggest position correction if needed

**OUTPUT FORMAT** (JSON only):
```json
{{
    "found": true/false,
    "position": [x, y, z],
    "confidence": 0-100,
    "description": "Detailed description with fine features",
    "bounding_box": [x1, y1, x2, y2],
    "grasp_recommendations": {{
        "best_grasp_points": "Description of optimal grasp locations",
        "approach_angle": "Recommended approach direction",
        "obstacles": "Any nearby obstacles or constraints"
    }},
    "refinement_notes": "How this refines the initial estimate"
}}
```

**IMPORTANT GUIDELINES**:
- This is the FINAL refinement - be as precise as possible
- Use the high detail to identify exact object boundaries
- Grasp planning information is critical for successful manipulation
- If object is not what was expected, clearly indicate this
- High confidence is expected due to close-up view
"""
        return prompt

    def get_multi_view_fusion_prompt(
        self,
        object_name: str,
        d455_result: Dict,
        head_result: Optional[Dict],
        wrist_result: Optional[Dict]
    ) -> str:
        """Get prompt for fusing multiple view results.

        This asks VLM to intelligently combine information from multiple views.

        Args:
            object_name: Name of object
            d455_result: Result from D455 camera
            head_result: Result from head camera (optional)
            wrist_result: Result from wrist camera (optional)

        Returns:
            Fusion prompt string
        """
        prompt = f"""You are analyzing MULTIPLE VIEWS of the same object to determine the most accurate location.

**TASK**: Synthesize information from multiple camera views to determine the best estimate for "{object_name}".

**AVAILABLE VIEWS**:

1. **D455 Overhead Camera** (Primary):
   - Position: {d455_result.get('position')}
   - Confidence: {d455_result.get('confidence')}%
   - Description: {d455_result.get('description')}
   - This view has depth information (most accurate for 3D position)

"""

        if head_result:
            prompt += f"""2. **Head Camera** (Validation):
   - Position: {head_result.get('position')}
   - Confidence: {head_result.get('confidence')}%
   - Description: {head_result.get('description')}
   - This is a secondary validation view

"""

        if wrist_result:
            prompt += f"""3. **Wrist Camera** (Refinement):
   - Position: {wrist_result.get('position')}
   - Confidence: {wrist_result.get('confidence')}%
   - Description: {wrist_result.get('description')}
   - This is a close-up detailed view

"""

        prompt += f"""**YOUR FUSION ANALYSIS**:

1. **Consistency Check**:
   - Are the views consistent with each other?
   - Calculate position differences between views
   - Identify any major discrepancies (>10cm difference)

2. **Confidence Weighting**:
   - D455 with depth: Highest weight for 3D position
   - Wrist close-up: Highest weight for fine details
   - Head camera: Validation only

3. **Final Position Estimate**:
   - Synthesize the most accurate position [x, y, z]
   - Prioritize D455 depth data for X, Y, Z
   - Use wrist camera to refine if available
   - Use head camera to validate

4. **Final Confidence**:
   - If views are consistent (< 5cm difference): High confidence (90-95%)
   - If views are somewhat consistent (5-15cm): Medium confidence (70-85%)
   - If views are inconsistent (> 15cm): Low confidence (< 70%)

**OUTPUT FORMAT** (JSON only):
```json
{{
    "found": true/false,
    "position": [x, y, z],
    "confidence": 0-100,
    "description": "Synthesized description from all views",
    "bounding_box": [x1, y1, x2, y2],
    "fusion_analysis": {{
        "view_consistency": "Assessment of how well views agree",
        "position_differences": "Differences between view estimates",
        "primary_view": "Which view was weighted most heavily",
        "confidence_reasoning": "Why this confidence level"
    }}
}}
```

**IMPORTANT**:
- Depth data from D455 is most reliable for 3D position
- Close-up wrist view is most reliable for fine details
- Inconsistent views should result in lower confidence
- Explain your reasoning for the final estimate
"""
        return prompt

    def get_scene_description_prompt(self) -> str:
        """Get prompt for general scene description.

        Returns:
            Scene description prompt
        """
        prompt = """Describe this scene from a robot manipulation perspective.

**PROVIDE**:
1. **Objects Present**: List all visible objects with descriptions
2. **Workspace Layout**: Describe the arrangement and spatial relationships
3. **Obstacles**: Note any obstacles or constraints
4. **Manipulation Opportunities**: Suggest which objects are graspable
5. **Scene Complexity**: Assess clutter level and manipulation difficulty

**FORMAT**: Natural language description (2-3 paragraphs)

Focus on actionable information for robot control."""

        return prompt

    def get_object_identification_prompt(self) -> str:
        """Get prompt for identifying all objects in scene.

        Returns:
            Object identification prompt
        """
        prompt = """Identify ALL objects visible in this image.

For each object, provide:
1. **Name/Type**: What is it?
2. **Color**: Primary color(s)
3. **Size**: Approximate size (small/medium/large)
4. **Location**: Where in the image (e.g., "center", "top-left")
5. **Graspable**: Can a robot grasp it? (yes/no)
6. **Distinctive Features**: Any notable characteristics

**OUTPUT FORMAT** (JSON array):
```json
[
    {{
        "name": "object name",
        "color": "color description",
        "size": "small/medium/large",
        "location": "location description",
        "graspable": true/false,
        "features": "distinctive features"
    }},
    ...
]
```

Be thorough - include all objects, even small or background items."""

        return prompt


# Test code
if __name__ == "__main__":
    print("Testing VLMPrompts...")

    # Initialize prompts
    prompts = VLMPrompts()

    # Test Phase 1 D455 prompt
    print("\n" + "=" * 60)
    print("PHASE 1 D455 PROMPT")
    print("=" * 60)
    prompt = prompts.get_phase1_d455_prompt("red cup")
    print(prompt[:500] + "...")

    # Test Phase 2 wrist prompt
    print("\n" + "=" * 60)
    print("PHASE 2 WRIST PROMPT")
    print("=" * 60)
    prompt = prompts.get_phase2_wrist_camera_prompt("red cup", [0.6, 0.0, 0.05])
    print(prompt[:500] + "...")

    # Test fusion prompt
    print("\n" + "=" * 60)
    print("MULTI-VIEW FUSION PROMPT")
    print("=" * 60)
    d455_result = {
        'position': [0.6, 0.0, 0.05],
        'confidence': 85,
        'description': 'Red cup in center of workspace'
    }
    prompt = prompts.get_multi_view_fusion_prompt("red cup", d455_result, None, None)
    print(prompt[:500] + "...")

    print("\n✓ VLMPrompts test completed")
