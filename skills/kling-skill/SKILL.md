---
name: kling_skill
description: Generate cinematic AI videos (text-to-video or image-to-video) using Kling AI 3.0 via the fal.ai API. Supports multi-shot generation, native audio, aspect ratio control, and image anchoring.
version: "1.0.0"
author: "Amir Khodabakhsh"
triggers:
  - "generate a kling video"
  - "create video with kling"
  - "kling text to video"
  - "kling image to video"
  - "kling 3.0"
  - "cinematic scene video"
  - "animate this image with kling"
user-invocable: true
metadata: { "openclaw": { "emoji": "🎥", "requires": { "bins": ["python3"], "env": ["FAL_KEY"] } } }
---

# Kling AI 3.0 — Video Generation Skill

## What It Does

Submits a Kling v3 video generation job via fal.ai's API, polls for completion,
and returns the video URL. Supports:

- Text-to-video (single prompt or multi-shot)
- Image-to-video (start_image_url, optional end_image_url)
- Native audio generation
- Aspect ratio: 16:9, 9:16, or 1:1
- Duration: 3–15 seconds (v3 standard) or 5–10 seconds (v3 pro image-to-video)

## Rules

- Never print or log FAL_KEY.
- Kling v3 uses FAL_KEY, NOT a separate Kling AccessKey/SecretKey for the fal.ai endpoint.
- Use fal.ai endpoint `fal-ai/kling-video/v3/standard/text-to-video` for text-to-video.
- Use fal.ai endpoint `fal-ai/kling-video/v3/standard/image-to-video` for image-to-video.
- Multi-shot uses `multi_prompt` list instead of `prompt`. Do not mix the two.
- If image-to-video, `start_image_url` must be a publicly accessible HTTPS URL.
- Do not invent video URLs. Return only what the API provides.
- If the job fails, return the exact error from the API.

## Inputs

Ask the user:

1. **Type**: text-to-video or image-to-video?
2. **Prompt**: scene description (for single) or list of shot descriptions (for multi-shot)
3. **Image URL** (if image-to-video): must be publicly accessible HTTPS
4. **End image URL** (optional, image-to-video only): anchor the last frame
5. **Duration**: 5–15 seconds (default: 5)
6. **Aspect ratio**: 16:9 (default) or 9:16 for TikTok
7. **Audio**: generate native audio? (default: true)
8. **Multi-shot**: yes/no — if yes, collect per-shot prompt + duration

## Workflow

### Step 1 — Install client if missing

```bash
pip install fal-client --quiet 2>/dev/null || true
```

### Step 2 — Text-to-Video (single prompt)

```python
import fal_client
import os

os.environ["FAL_KEY"] = os.getenv("FAL_KEY", "")

result = fal_client.subscribe(
    "fal-ai/kling-video/v3/standard/text-to-video",
    arguments={
        "prompt": "<USER_PROMPT>",
        "duration": "5",
        "aspect_ratio": "9:16",
        "generate_audio": True,
        "negative_prompt": "blur, distort, low quality",
        "cfg_scale": 0.5
    },
    with_logs=True,
    on_queue_update=lambda update: print(f"Status: {update.status}") if hasattr(update, 'status') else None
)

video_url = result["video"]["url"]
print(f"Video URL: {video_url}")
```

### Step 2 — Multi-Shot Text-to-Video

```python
import fal_client
import os

os.environ["FAL_KEY"] = os.getenv("FAL_KEY", "")

# multi_prompt list — define per shot
multi_prompt = [
    {"prompt": "<SHOT_1_DESCRIPTION>", "duration": "3"},
    {"prompt": "<SHOT_2_DESCRIPTION>", "duration": "4"},
    {"prompt": "<SHOT_3_DESCRIPTION>", "duration": "3"}
]

result = fal_client.subscribe(
    "fal-ai/kling-video/v3/standard/text-to-video",
    arguments={
        "multi_prompt": multi_prompt,
        "shot_type": "customize",
        "aspect_ratio": "9:16",
        "generate_audio": True,
        "negative_prompt": "blur, distort, low quality"
    },
    with_logs=True,
    on_queue_update=lambda update: print(f"Status: {update.status}") if hasattr(update, 'status') else None
)

video_url = result["video"]["url"]
print(f"Multi-shot video URL: {video_url}")
```

### Step 2 — Image-to-Video

```python
import fal_client
import os

os.environ["FAL_KEY"] = os.getenv("FAL_KEY", "")

result = fal_client.subscribe(
    "fal-ai/kling-video/v3/standard/image-to-video",
    arguments={
        "prompt": "<ANIMATION_DESCRIPTION>",
        "start_image_url": "<IMAGE_URL>",
        # "end_image_url": "<OPTIONAL_END_FRAME_URL>",
        "duration": "5",
        "generate_audio": True,
        "negative_prompt": "blur, distort, low quality",
        "cfg_scale": 0.5
    },
    with_logs=True,
    on_queue_update=lambda update: print(f"Status: {update.status}") if hasattr(update, 'status') else None
)

video_url = result["video"]["url"]
print(f"Image-to-video URL: {video_url}")
```

### Step 3 — Return result

```
✅ Kling 3.0 video ready.
URL: <video_url>
File size: <file_size> bytes
Mode: text-to-video | Aspect: 9:16 | Duration: 5s
```

## Key Notes

- Kling v3 supports **multi-shot** — explicit per-shot prompts in one generation pass.
- `generate_audio`: true creates native audio (English/Chinese speech supported).
- `elements` field allows character/object locking — reference as `@Element1` in prompt.
- `end_image_url` anchors the last frame of an image-to-video generation.
- `cfg_scale` default: 0.5 (range 0–1, higher = follows prompt more strictly).
- `negative_prompt` default: `"blur, distort, and low quality"` — add keywords to exclude.
- fal.ai auto-manages the queue — no manual task ID polling required with `fal_client.subscribe`.
