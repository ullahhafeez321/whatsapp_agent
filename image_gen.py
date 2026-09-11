import io
import logging
import os
import threading
import time
from urllib.parse import quote

import requests

logger = logging.getLogger(__name__)

_API_URL = "https://image.pollinations.ai/prompt"
_MIN_RATE_LIMIT_INTERVAL = 15.0
_last_request_time = 0.0
_lock = threading.Lock()


def generate_image(prompt, output_path=None, width=1024, height=1024,
                   model="flux", seed=None, timeout=120):
  """Generate an image via Pollinations.ai. No API key required.

  Returns bytes. If output_path is given, also writes the file and returns bytes.
  """
  global _last_request_time

  with _lock:
    elapsed = time.time() - _last_request_time
    if elapsed < _MIN_RATE_LIMIT_INTERVAL:
      wait = _MIN_RATE_LIMIT_INTERVAL - elapsed
      logger.info(f"Image rate limit: waiting {wait:.1f}s")
      time.sleep(wait)
    _last_request_time = time.time()

  params = {
      "model": model,
      "width": width,
      "height": height,
      "enhance": "true",
      "safe": "true",
      "private": "true",
  }
  if seed is not None:
    params["seed"] = seed

  url = f"{_API_URL}/{quote(prompt)}"
  logger.info(f"Generating image with Pollinations (model={model}, {width}x{height})")

  response = requests.get(url, params=params, timeout=timeout)
  if response.status_code != 200:
    raise RuntimeError(f"Pollinations error {response.status_code}: {response.text[:300]}")

  data = response.content
  if len(data) < 2000:
    raise RuntimeError("Pollinations returned an invalid/rate-limited placeholder image")

  if output_path:
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "wb") as f:
      f.write(data)
    logger.info(f"Saved image to {output_path} ({len(data)} bytes)")
  else:
    logger.info(f"Image generated ({len(data)} bytes)")

  return data


def generate_image_bytes_io(prompt, timeout=120):
  """Convenience wrapper returning io.BytesIO (for direct upload)."""
  data = generate_image(prompt, timeout=timeout)
  return io.BytesIO(data)