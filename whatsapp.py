import logging
import mimetypes
import os
import time

import requests

import config

logger = logging.getLogger(__name__)

MEDIA_MAX_RETRIES = 3


def _post(endpoint, payload, max_retries=3):
  """POST JSON to the WhatsApp gateway with exponential backoff on failures."""
  url = f"{config.BASE_URL}/{endpoint}"
  for attempt in range(max_retries + 1):
    try:
      response = requests.post(url, headers=config.HEADERS, json=payload, timeout=60)
      if response.status_code in (429, 500, 502, 503, 504):
        wait = min(2 ** attempt * 2, 30)
        logger.warning(f"{endpoint} transient error {response.status_code}, retrying in {wait}s")
        time.sleep(wait)
        continue
      return response
    except requests.exceptions.RequestException as e:
      wait = min(2 ** attempt * 2, 30)
      logger.warning(f"{endpoint} network error: {e}, retrying in {wait}s")
      time.sleep(wait)
  return None


def mark_read_and_typing(message_id):
  """Mark the message as read and show a typing indicator."""
  payload = {
      "messaging_product": "whatsapp",
      "status": "read",
      "message_id": message_id,
      "typing_indicator": {"type": "text"},
  }
  try:
    requests.post(f"{config.BASE_URL}/statuses", headers=config.HEADERS, json=payload, timeout=30)
  except requests.exceptions.RequestException as e:
    logger.warning(f"Could not send status/typing: {e}")


def send_text(recipient_id, text_body):
  """Send a plain text message."""
  payload = {
      "messaging_product": "whatsapp",
      "to": recipient_id,
      "type": "text",
      "text": {"body": text_body},
  }
  return _post("messages", payload)


def upload_media(file_path, mime_type):
  """Upload a file to the gateway and return its media id (or None)."""
  url = f"{config.BASE_URL}/media"
  headers = {"Authorization": config.HEADERS["Authorization"]}
  for attempt in range(MEDIA_MAX_RETRIES + 1):
    try:
      with open(file_path, "rb") as f:
        files = {"file": (os.path.basename(file_path), f, mime_type)}
        data = {"messaging_product": "whatsapp", "type": mime_type}
        response = requests.post(url, headers=headers, files=files, data=data, timeout=120)
      if response.status_code in (429, 500, 502, 503, 504):
        wait = min(2 ** attempt * 2, 30)
        logger.warning(f"Upload transient error {response.status_code}, retrying in {wait}s")
        time.sleep(wait)
        continue
      if response.status_code != 200 and response.status_code != 201:
        logger.error(f"Upload failed {response.status_code}: {response.text[:300]}")
        return None
      media_id = response.json().get("id")
      logger.info(f"Uploaded {os.path.basename(file_path)} -> media id {media_id}")
      return media_id
    except (requests.exceptions.RequestException, OSError) as e:
      wait = min(2 ** attempt * 2, 30)
      logger.warning(f"Upload error: {e}, retrying in {wait}s")
      time.sleep(wait)
  return None


def send_image(recipient_id, file_path, caption=None):
  """Upload an image and send it. Returns True on success."""
  mime_type = mimetypes.guess_type(file_path)[0] or "image/jpeg"
  media_id = upload_media(file_path, mime_type)
  if media_id is None:
    return False
  image = {"id": media_id}
  if caption:
    image["caption"] = caption
  payload = {
      "messaging_product": "whatsapp",
      "to": recipient_id,
      "type": "image",
      "image": image,
  }
  response = _post("messages", payload)
  return bool(response and response.status_code == 200)


def send_document(recipient_id, file_path, filename=None, caption=None):
  """Upload a document (PDF) and send it. Returns True on success."""
  mime_type = mimetypes.guess_type(file_path)[0] or "application/pdf"
  media_id = upload_media(file_path, mime_type)
  if media_id is None:
    return False
  document = {"id": media_id, "filename": filename or os.path.basename(file_path)}
  if caption:
    document["caption"] = caption
  payload = {
      "messaging_product": "whatsapp",
      "to": recipient_id,
      "type": "document",
      "document": document,
  }
  response = _post("messages", payload)
  return bool(response and response.status_code == 200)