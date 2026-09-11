import json
import logging
import re
import time

import config

logger = logging.getLogger(__name__)

MAX_CHAT_RETRIES = 3


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
    """Send a message with retry on transient errors; return raw text response."""
    chat = self.get_or_create_chat(user_id)
    last_error = None
    for attempt in range(MAX_CHAT_RETRIES):
      try:
        response = chat.send_message(message)
        return response.text.strip() if response.text else ""
      except Exception as e:
        last_error = e
        if not self._is_transient(e):
          logger.error(f"Gemini chat error for {user_id}: {e}")
          raise
        wait = min(2 ** attempt * 2, 30)
        logger.warning(
            f"Gemini transient error for {user_id} (attempt {attempt + 1}/"
            f"{MAX_CHAT_RETRIES}): {e} — retrying in {wait}s")
        time.sleep(wait)
    raise last_error

  @staticmethod
  def _is_transient(error):
    """Return True for 429/5xx/network errors where a retry may succeed."""
    status = getattr(error, "status_code", None)
    if status is not None:
      return status == 429 or 500 <= status < 600
    return isinstance(error, (ConnectionError, TimeoutError))

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

    candidates = self._extract_json_candidates(response_text)
    for candidate in candidates:
      try:
        data = json.loads(candidate)
        if isinstance(data, dict) and data.get("action") in ("generate_image", "generate_document"):
          return data
      except json.JSONDecodeError:
        continue
    return None

  def _extract_json_candidates(self, text):
    """Yield plausible JSON substrings: raw, fenced, and brace-balanced blocks."""
    text = text.strip()
    yield text

    fence = re.search(r'```(?:json)?\s*(.*?)```', text, re.DOTALL | re.IGNORECASE)
    if fence:
      yield fence.group(1).strip()

    for match in re.finditer(r'\{', text):
      candidate = self._balanced_json(text, match.start())
      if candidate:
        yield candidate

  def _balanced_json(self, text, start):
    """Return the brace-balanced substring starting at text[start] if it ends cleanly."""
    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(text)):
      char = text[i]
      if in_string:
        if escape:
          escape = False
        elif char == "\\":
          escape = True
        elif char == '"':
          in_string = False
        continue
      if char == '"':
        in_string = True
      elif char == "{":
        depth += 1
      elif char == "}":
        depth -= 1
        if depth == 0:
          return text[start:i + 1]
    return None

  def reply(self, user_id, message):
    """Full pipeline: chat with Gemini and either return text or a tool action."""
    response_text = self.chat(user_id, message)
    action = self.parse_action(response_text)
    if action:
      return action, None
    return None, response_text