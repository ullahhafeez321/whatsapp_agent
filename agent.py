import logging
import os
import tempfile
import time

import config
import docx_gen
import image_gen
import whatsapp
from llm import LLMAgent

logger = logging.getLogger(__name__)

agent = LLMAgent()

SEEN_TTL_SECONDS = 7 * 24 * 3600
_seen_messages = {}


def is_duplicate(message_id):
  """Idempotency guard: skip messages already processed within the TTL window."""
  now = time.time()
  stale = [mid for mid, ts in _seen_messages.items() if now - ts > SEEN_TTL_SECONDS]
  for mid in stale:
    del _seen_messages[mid]
  if message_id in _seen_messages:
    logger.info(f"Skipping duplicate message {message_id}")
    return True
  _seen_messages[message_id] = now
  return False


def _save_temp(data, suffix):
  """Write bytes to a temp file and return its path."""
  fd, path = tempfile.mkstemp(suffix=suffix)
  with os.fdopen(fd, "wb") as f:
    f.write(data)
  return path


def _handle_text_message(sender_id, message_id, text):
  whatsapp.mark_read_and_typing(message_id)
  agent.expire_sessions()

  action, reply_text = agent.reply(sender_id, text)

  if action:
    action_type = action.get("action")
    try:
      if action_type == "generate_image":
        whatsapp.send_text(
            sender_id, "One moment while I generate your image...")
        return _generate_and_send_image(sender_id, action)
      elif action_type == "generate_document":
        whatsapp.send_text(sender_id, "One moment while I create your document...")
        return _generate_and_send_document(sender_id, action)
    except Exception as e:
      logger.exception(f"Tool action failed for {sender_id}: {e}")
      whatsapp.send_text(sender_id, "Sorry, I ran into an error while doing that. Please try again in a moment.")
      return
  else:
    whatsapp.send_text(sender_id, reply_text)


def _generate_and_send_image(sender_id, action):
  prompt = action.get("prompt")
  if not prompt:
    whatsapp.send_text(sender_id, "Sorry, I couldn't understand the image request. Please try again.")
    return

  try:
    data = image_gen.generate_image(prompt)
  except Exception as e:
    logger.error(f"Image generation failed for {sender_id}: {e}")
    whatsapp.send_text(sender_id, "Sorry, image generation is temporarily unavailable. Please try again in a moment.")
    return

  path = _save_temp(data, ".jpg")
  try:
    if whatsapp.send_image(sender_id, path, caption=prompt[:300]):
      logger.info(f"Sent generated image to {sender_id}")
    else:
      whatsapp.send_text(sender_id, "Sorry, I couldn't deliver the image. Please try again.")
  finally:
    os.remove(path)


def _generate_and_send_document(sender_id, action):
  title = action.get("title", "Document")
  elements = action.get("elements", [])
  if not elements:
    whatsapp.send_text(sender_id, "Sorry, I couldn't compile the document. Please try again.")
    return

  try:
    docx_data = docx_gen.generate_docx(title, elements)
  except Exception as e:
    logger.error(f"Document generation failed for {sender_id}: {e}")
    whatsapp.send_text(sender_id, "Sorry, I couldn't create the document. Please try again.")
    return

  filename = f"{title.replace(' ', '_')[:40]}.docx"
  path = _save_temp(docx_data, ".docx")
  try:
    if whatsapp.send_document(sender_id, path, filename=filename, caption=title):
      logger.info(f"Sent generated document to {sender_id}: {filename}")
    else:
      whatsapp.send_text(sender_id, "Sorry, I couldn't deliver the document. Please try again.")
  finally:
    os.remove(path)


def handle_incoming_messages(messages):
  """Process a list of inbound messages from the gateway."""
  for msg in messages:
    sender_id = msg.get("from")
    message_id = msg.get("id")
    msg_type = msg.get("type", "")

    if not sender_id or not message_id or is_duplicate(message_id):
      continue

    logger.info(f"Received message {message_id} from {sender_id} of type '{msg_type}'")

    if msg_type == "text":
      text = (msg.get("text") or {}).get("body", "")
      try:
        _handle_text_message(sender_id, message_id, text)
      except Exception:
        logger.exception(f"Unhandled error processing message {message_id} from {sender_id}")
        whatsapp.send_text(
            sender_id,
            "I'm having trouble reaching my AI right now (likely high demand). "
            "Please try again in a moment. 🙏")

    elif msg_type in ("image", "audio", "video", "document", "sticker", "location", "contacts"):
      whatsapp.mark_read_and_typing(message_id)
      whatsapp.send_text(
          sender_id,
          "Thanks for that! I currently work best with text. "
          "You can ask me questions, or request an image or a Word document.")

    else:
      logger.info(f"Ignoring unsupported message type: {msg_type}")