---
name: runway_skill
description: Generate high-quality AI videos from text or images using Runway Gen-4 via the official RunwayML Python SDK. Best for precise cinematic single-shot generation with first/last frame control.
version: "1.0.0"
author: "Amir Khodabakhsh"
triggers:
  - "generate a runway video"
  - "make a video with runway"
  - "runway gen-4"
  - "runway image to video"
  - "cinematic single shot"
  - "first frame anchored video"
user-invocable: true
metadata:
  {
    "openclaw":
      { "emoji": "✈️", "requires": { "bins": ["python3"], "env": ["RUNWAYML_API_SECRET"] } },
  }
---

# Runway Gen-4 — Video Generation Skill

## What It Does

Generates video from an image input using the official `runwayml` Python SDK.
Uses `image_to_video.create()` + `wait_for_task_output()` for clean async resolution.
Returns the output video URL.

## Rules

- Never print or log RUNWAYML_API_SECRET.
- Runway uses RUNWAYML_API_SECRET, NOT RUNWAYML_API_KEY. The env var name is exact.
- Runway maintains a SEPARATE API billing balance from subscriptions. If requests fail with 402 or credit errors, direct user to dev.runwayml.com → API Usage to add credits.
- Max 5 concurrent requests on standard accounts. HTTP 429 = wait 15s, retry with backoff.
- Output URLs from Runway expire within hours. Download the file immediately after generation.
- Do not use this skill for long-form multi-scene generation — Kling handles that better.
- Do not invent video URLs. Return only what the SDK provides.

## Inputs

Ask the user:

1. **Image URL**: publicly accessible HTTPS image to anchor the video
2. **Prompt**: describe the motion and scene (plain English, no negative phrases)
3. **Duration**: 5 or 10 seconds (default: 5)
4. **Ratio**: `1280:720` (16:9 landscape) or `720:1280` (9:16 vertical) — default: `720:1280`
5. **Motion intensity** (optional): motion_bucket_id 1–255 (default: 127)
   - 1–50: subtle (breathing, clouds)
   - 120–150: standard motion (walking, talking)
   - 200+: high energy (fast action)
6. **Seed** (optional): integer for reproducibility

## Workflow

### Step 1 — Install SDK if missing

```bash
pip install runwayml --quiet 2>/dev/null || true
```

### Step 2 — Generate video

```python
import runwayml
import os

client = runwayml.RunwayML(api_key=os.environ["RUNWAYML_API_SECRET"])

task = client.image_to_video.create(
    model="gen4_turbo",
    prompt_image="<IMAGE_URL>",             # must be publicly accessible HTTPS
    prompt_text="<SCENE_AND_MOTION_DESCRIPTION>",
    duration=5,                              # 5 or 10
    ratio="720:1280",                        # 720:1280 for 9:16 vertical TikTok
    # seed=12345                             # optional for reproducibility
)

task_id = task.id
print(f"Task submitted: {task_id}")

# Poll with built-in helper
task = task.wait_for_task_output(timeout=600)

if task.status == "SUCCEEDED":
    print(f"Video URL: {task.output[0]}")
else:
    print(f"Failed: {task.failure_code} — {task.failure_message}")
```

### Step 3 — Download immediately (output URLs expire)

```python
import urllib.request

output_url = task.output[0]
filename = f"runway_{task_id[:8]}.mp4"
urllib.request.urlretrieve(output_url, filename)
print(f"Saved: {filename}")
```

### Step 4 — Return result

```
✅ Runway Gen-4 video ready.
URL: <output_url>
File: runway_<task_id[:8]>.mp4
Model: gen4_turbo | Duration: 5s | Ratio: 720:1280
⚠️  URL expires in ~1 hour. File has been saved locally.
```

## Error Handling

| Error             | Cause                         | Action                                      |
| ----------------- | ----------------------------- | ------------------------------------------- |
| 401               | Bad API secret                | Check RUNWAYML_API_SECRET                   |
| 402               | No API credits                | Direct user to dev.runwayml.com → API Usage |
| 429               | Rate limit (5 concurrent max) | Wait 15s, retry with backoff                |
| TaskFailedError   | Generation failed             | Print failure_code + failure_message        |
| TaskTimedOutError | >10 min                       | Try a simpler prompt or shorter duration    |

## Key Notes

- `motion_bucket_id` controls motion intensity — use it if you get too much/too little movement.
- `seed` locks composition — use this when regenerating for consistency.
- The SDK's `wait_for_task_output()` polls automatically with safe intervals.
- Runway is best for single-shot precision with a known reference image — use Kling for multi-shot scenes.
- Do NOT write negative phrases in the prompt ("no camera movement") — Runway interprets them literally and often inverts them. Write what you WANT instead.
