---
name: invideo_skill
description: Generate marketing and TikTok videos using the InVideo AI API from text prompts or structured scripts. Handles async job polling and returns a download URL.
version: "1.0.0"
author: "Amir Khodabakhsh"
triggers:
  - "create a video with invideo"
  - "generate invideo video"
  - "make a marketing video"
  - "build a tiktok video with invideo"
  - "invideo generate"
user-invocable: true
metadata:
  {
    "openclaw":
      { "emoji": "🎬", "requires": { "bins": ["python3", "curl"], "env": ["INVIDEO_API_KEY"] } },
  }
---

# InVideo AI — Video Generation Skill

## What It Does

Submits a video generation job to InVideo AI via the official Python SDK, polls for
completion, and returns the download URL. Supports text prompts, workflow selection,
resolution, aspect ratio, and voice settings.

## Rules

- Never print or log INVIDEO_API_KEY.
- If the API returns a 429, wait 30 seconds and retry once with exponential backoff.
- Free tier produces watermarked videos. Inform the user if they ask.
- Do not invent video URLs. Return only what the API provides.
- If the job fails, return the exact error message from the API.

## Inputs

Ask the user for:

1. `prompt` — full text description or script for the video
2. `workflow` (optional) — default: `text-to-video-v6`
3. `resolution` (optional) — default: `1080p`
4. `aspect_ratio` (optional) — `16:9` (default) or `9:16` for TikTok/Reels
5. `voice_id` (optional) — e.g. `sarah_news_anchor_v2`

If not provided, use the defaults above.

## Workflow

### Step 1 — Verify the environment variable

```python
import os
key = os.getenv("INVIDEO_API_KEY")
if not key:
    print("ERROR: INVIDEO_API_KEY is not set. Add it to openclaw.json under skills.entries.invideo-skill.env")
    exit(1)
print("API key found.")
```

### Step 2 — Submit the job

```python
import os
from invideo import InVideoClient

client = InVideoClient(api_key=os.getenv("INVIDEO_API_KEY"))

payload = {
    "workflow": "text-to-video-v6",
    "input_text": "<USER_PROMPT>",
    "settings": {
        "resolution": "1080p",
        "aspect_ratio": "9:16",    # use 16:9 for landscape, 9:16 for TikTok
        "voice_id": "sarah_news_anchor_v2"
    }
}

job = client.videos.create(payload)
print(f"Job submitted. ID: {job.id} | Status: {job.status}")
```

### Step 3 — Poll for completion

```python
video = client.videos.wait_for_completion(job.id)
print(f"Video ready: {video.download_url}")
```

### Step 4 — Return result to user

Print the `download_url` clearly. Do not add any other commentary.

## Output Format

```
✅ InVideo video ready.
Download URL: <url>
Job ID: <job_id>
Resolution: 1080p | Aspect ratio: 9:16
```

## Error Codes

| Code | Meaning       | Action                            |
| ---- | ------------- | --------------------------------- |
| 401  | Bad API key   | Ask user to check INVIDEO_API_KEY |
| 429  | Rate limit    | Wait 30s, retry once              |
| 500  | Render failed | Return error message verbatim     |

## Key Notes

- The InVideo free tier adds watermarks. Paid plan required for clean export.
- `negative_prompt` field can exclude keywords like `"cartoon, animation"`.
- Webhook support available — not required for simple agent use.
- API rate limits on Pro tier are strict for high-volume batches.
