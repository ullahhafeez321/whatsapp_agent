import json
import logging
import re
import time

import config

logger = logging.getLogger(__name__)


class LLMAgent:
  """Google Gemini-powered conversational agent with per-user memory."""

  SESSION_TTL_SECONDS = 30 * 60

  def __init__(self):
    self._client = None
    self._sessions = {}
    self._last_activity = {}

  @property
  def client(self):
    if self._client is None:
      from google import genai
      self._client = genai.Client(api_key=config.GEMINI_API_KEY)
    return self._client

  def get_or_create_chat(self, user_id):
    now = time.time()
    if user_id in self._sessions:
      self._last_activity[user_id] = now
      return self._sessions[user_id]

    from google.genai import types
    chat = self.client.chats.create(
        model=config.GEMINI_MODEL,
        config=types.GenerateContentConfig(
            system_instruction=config.SYSTEM_PROMPT,
            temperature=0.7,
            max_output_tokens=2048,
        ),
    )
    self._sessions[user_id] = chat
    self._last_activity[user_id] = now
    return chat

  def expire_sessions(self):
    """Remove chat sessions idle for longer than SESSION_TTL_SECONDS."""
    now = time.time()
    stale = [
        uid for uid, last in self._last_activity.items()
        if now - last > self.SESSION_TTL_SECONDS
    ]
    for uid in stale:
      self._sessions.pop(uid, None)
      self._last_activity.pop(uid, None)
      if len(self._sessions) < 20:
        logger.info(f"Expired idle session for {uid}")
      else:
        logger.info(f"Expired {len(stale)} idle sessions")

  def chat(self, user_id, message):
    """Send a message and return the model's raw text response."""
    chat = self.get_or_create_chat(user_id)
    try:
      response = chat.send_message(message)
      return response.text.strip() if response.text else ""
    except Exception as e:
      logger.error(f"Gemini chat error for {user_id}: {e}")
      raise

  def reset_chat(self, user_id):
    self._sessions.pop(user_id, None)
    self._last_activity.pop(user_id, None)
    logger.info(f"Reset session for {user_id}")

  def parse_action(self, response_text):
    """Extract a tool-action JSON from Gemini output, if present.

    Returns a dict like {"action": "generate_image", "prompt": "..."} or
    {"action": "generate_document", "title": "...", "elements": [...]}, or None
    if the response is plain conversational text.
    """
    if not response_text:
      return None

    text = response_text.strip()

    try:
      data = json.loads(text)
      if isinstance(data, dict) and data.get("action") in ("generate_image", "generate_document"):
        return data
    except json.JSONDecodeError:
      pass

    match = re.search(r'\{[^{}]*"action"\s*:\s*"[^{}]*\"[^{}]*\}', text)
    if match:
      try:
        data = json.loads(match.group(0))
        if isinstance(data, dict) and data.get("action") in ("generate_image", "generate_document"):
          return data
      except json.JSONDecodeError:
        pass

    return None

  def reply(self, user_id, message):
    """Full pipeline: chat with Gemini and either return text or a tool action."""
    response_text = self.chat(user_id, message)
    action = self.parse_action(response_text)
    if action:
      return action, None
    return None, response_text