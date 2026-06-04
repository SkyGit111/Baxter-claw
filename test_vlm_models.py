#!/usr/bin/env python3
"""
Test different VLM models to find the best one for object detection.
Tests with your current API key to see which models work and return correct format.
"""

import asyncio
import base64
import httpx
import json
from pathlib import Path

# Test image - use one of your existing debug images
TEST_IMAGE_PATH = "debug_d455_phase1_raw.jpg"
TEST_OBJECT = "黄色小方块"

# Models to test
MODELS_TO_TEST = {
    "OpenAI": [
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-4-turbo",
    ],
    "Anthropic": [
        "claude-3-5-sonnet-20241022",
        "claude-3-5-haiku-20241022",
        "claude-3-opus-20240229",
    ],
    "Qwen": [
        "qwen-vl-max",
        "qwen-vl-plus",
    ]
}

PROMPT = f"""You are a robot vision system. Your ONLY task is to locate the {TEST_OBJECT}.

CRITICAL REQUIREMENTS:
1. You MUST find and locate the {TEST_OBJECT} - this is mandatory
2. Be FLEXIBLE with matching: if you see anything that could reasonably be "{TEST_OBJECT}", that counts
3. For colors: accept similar shades (e.g., "黄色" includes yellow, golden, amber, light orange)
4. For shapes: "小方块" means any small cube, block, or box-like object
5. If you see MULTIPLE candidates, pick the most likely one
6. You MUST set found=true and provide a real position - [0,0,0] is NOT acceptable
7. If uncertain, use lower confidence (30-70) but still return found=true

Your task: Find the {TEST_OBJECT} in this image and provide its location.

OUTPUT FORMAT (respond with ONLY valid JSON, no markdown):
{{
    "found": true,
    "position": [x, y, z],
    "confidence": 30-100,
    "description": "what you see and why you picked it",
    "bounding_box": [x1, y1, x2, y2]
}}

REMEMBER: You MUST return found=true with a real position. Saying "not found" is NOT an option.
"""


async def test_openai_model(model: str, image_b64: str, api_key: str) -> dict:
    """Test an OpenAI model."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": PROMPT},
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{image_b64}"
                                    }
                                }
                            ]
                        }
                    ],
                    "max_tokens": 1024,
                }
            )

            if response.status_code != 200:
                return {"error": f"HTTP {response.status_code}: {response.text[:200]}"}

            result = response.json()
            content = result['choices'][0]['message']['content']

            # Try to parse JSON
            try:
                parsed = json.loads(content)
                return {"success": True, "response": parsed}
            except:
                return {"error": "Invalid JSON response", "raw": content[:200]}

    except Exception as e:
        return {"error": str(e)}


async def test_claude_model(model: str, image_b64: str, api_key: str) -> dict:
    """Test a Claude model."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": model,
                    "max_tokens": 1024,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "image",
                                    "source": {
                                        "type": "base64",
                                        "media_type": "image/jpeg",
                                        "data": image_b64,
                                    }
                                },
                                {"type": "text", "text": PROMPT}
                            ]
                        }
                    ]
                }
            )

            if response.status_code != 200:
                return {"error": f"HTTP {response.status_code}: {response.text[:200]}"}

            result = response.json()
            content = result['content'][0]['text']

            # Try to parse JSON
            try:
                # Remove markdown code blocks if present
                if '```json' in content:
                    content = content.split('```json')[1].split('```')[0].strip()
                elif '```' in content:
                    content = content.split('```')[1].split('```')[0].strip()

                parsed = json.loads(content)
                return {"success": True, "response": parsed}
            except:
                return {"error": "Invalid JSON response", "raw": content[:200]}

    except Exception as e:
        return {"error": str(e)}


async def test_qwen_model(model: str, image_b64: str, api_key: str) -> dict:
    """Test a Qwen model."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "input": {
                        "messages": [
                            {
                                "role": "user",
                                "content": [
                                    {"image": f"data:image/jpeg;base64,{image_b64}"},
                                    {"text": PROMPT}
                                ]
                            }
                        ]
                    }
                }
            )

            if response.status_code != 200:
                return {"error": f"HTTP {response.status_code}: {response.text[:200]}"}

            result = response.json()
            content = result['output']['choices'][0]['message']['content'][0]['text']

            # Try to parse JSON
            try:
                parsed = json.loads(content)
                return {"success": True, "response": parsed}
            except:
                return {"error": "Invalid JSON response", "raw": content[:200]}

    except Exception as e:
        return {"error": str(e)}


async def main():
    print("="*70)
    print("VLM MODEL TESTING")
    print("="*70)
    print(f"\nTest object: {TEST_OBJECT}")
    print(f"Test image: {TEST_IMAGE_PATH}\n")

    # Load test image
    if not Path(TEST_IMAGE_PATH).exists():
        print(f"❌ Test image not found: {TEST_IMAGE_PATH}")
        print("Please provide a valid image path or use one of your debug images.")
        return

    with open(TEST_IMAGE_PATH, 'rb') as f:
        image_bytes = f.read()
    image_b64 = base64.b64encode(image_bytes).decode('utf-8')

    # Load API keys from config
    try:
        import yaml
        with open('config/baxter.yaml', 'r') as f:
            config = yaml.safe_load(f)

        openai_key = config.get('vlm', {}).get('openai_api_key', '')
        claude_key = config.get('vlm', {}).get('claude_api_key', '')
        qwen_key = config.get('vlm', {}).get('qwen_api_key', '')
    except:
        print("❌ Could not load API keys from config/baxter.yaml")
        return

    results = {}

    # Test OpenAI models
    if openai_key:
        print("\n" + "="*70)
        print("TESTING OPENAI MODELS")
        print("="*70)
        for model in MODELS_TO_TEST["OpenAI"]:
            print(f"\n[{model}]")
            result = await test_openai_model(model, image_b64, openai_key)
            results[f"OpenAI/{model}"] = result

            if result.get("success"):
                resp = result["response"]
                print(f"  ✓ Success!")
                print(f"    Found: {resp.get('found')}")
                print(f"    Confidence: {resp.get('confidence')}")
                print(f"    Position: {resp.get('position')}")
            else:
                print(f"  ✗ Failed: {result.get('error', 'Unknown error')}")

    # Test Claude models
    if claude_key:
        print("\n" + "="*70)
        print("TESTING ANTHROPIC CLAUDE MODELS")
        print("="*70)
        for model in MODELS_TO_TEST["Anthropic"]:
            print(f"\n[{model}]")
            result = await test_claude_model(model, image_b64, claude_key)
            results[f"Anthropic/{model}"] = result

            if result.get("success"):
                resp = result["response"]
                print(f"  ✓ Success!")
                print(f"    Found: {resp.get('found')}")
                print(f"    Confidence: {resp.get('confidence')}")
                print(f"    Position: {resp.get('position')}")
            else:
                print(f"  ✗ Failed: {result.get('error', 'Unknown error')}")

    # Test Qwen models
    if qwen_key:
        print("\n" + "="*70)
        print("TESTING QWEN MODELS")
        print("="*70)
        for model in MODELS_TO_TEST["Qwen"]:
            print(f"\n[{model}]")
            result = await test_qwen_model(model, image_b64, qwen_key)
            results[f"Qwen/{model}"] = result

            if result.get("success"):
                resp = result["response"]
                print(f"  ✓ Success!")
                print(f"    Found: {resp.get('found')}")
                print(f"    Confidence: {resp.get('confidence')}")
                print(f"    Position: {resp.get('position')}")
            else:
                print(f"  ✗ Failed: {result.get('error', 'Unknown error')}")

    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)

    successful = [k for k, v in results.items() if v.get("success")]
    failed = [k for k, v in results.items() if not v.get("success")]

    print(f"\n✓ Successful models ({len(successful)}):")
    for model in successful:
        resp = results[model]["response"]
        found = resp.get('found', False)
        conf = resp.get('confidence', 0)
        print(f"  - {model}: found={found}, confidence={conf}")

    print(f"\n✗ Failed models ({len(failed)}):")
    for model in failed:
        error = results[model].get('error', 'Unknown')
        print(f"  - {model}: {error[:50]}")

    if successful:
        print(f"\n🏆 RECOMMENDED: Use {successful[0]}")
    else:
        print("\n❌ No models succeeded. Check API keys and network connection.")


if __name__ == "__main__":
    asyncio.run(main())
