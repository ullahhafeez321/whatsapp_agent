import logging
import signal
import sys
import time

import requests

import agent
import config

logger = logging.getLogger("whatsapp_agent")
_keep_running = True


def signal_handler(signum, frame):
  global _keep_running
  logger.info("Shutdown signal received, stopping...")
  _keep_running = False


def poll_updates(offset=None):
  """Long-polls the gateway for new messages."""
  params = {"timeout": 15}
  if offset is not None:
    params["offset"] = offset

  try:
    response = requests.get(
        f"{config.BASE_URL}/updates",
        headers=config.HEADERS,
        params=params,
        timeout=25,
    )
  except requests.exceptions.RequestException as e:
    logger.warning(f"Network error during polling: {e}")
    time.sleep(5)
    return offset

  if response.status_code == 204:
    return offset

  if response.status_code != 200:
    logger.error(f"Error polling updates: {response.status_code} - {response.text}")
    time.sleep(5)
    return offset

  data = response.json()
  next_offset = data.get("next_offset")

  for entry in data.get("entry", []):
    for change in entry.get("changes", []):
      if change.get("field") == "messages":
        value = change.get("value", {})
        messages = value.get("messages", [])
        if messages:
          agent.handle_incoming_messages(messages)

  return next_offset


def main():
  logging.basicConfig(
      level=logging.INFO,
      format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
      handlers=[logging.StreamHandler(sys.stdout)],
  )

  if not config.API_TOKEN:
    logger.error("WHATSAPP_API_TOKEN is not set in .env. Exiting.")
    sys.exit(1)
  if not config.GEMINI_API_KEY or "your_gemini_api_key" in config.GEMINI_API_KEY:
    logger.error(
        "GEMINI_API_KEY is not set in .env (get a free key at "
        "https://aistudio.google.com/app/apikeys). Exiting."
    )
    sys.exit(1)

  signal.signal(signal.SIGINT, signal_handler)
  signal.signal(signal.SIGTERM, signal_handler)

  logger.info("Starting WhatsApp Agent listener...")
  current_offset = None

  while _keep_running:
    current_offset = poll_updates(current_offset)
    time.sleep(1)

  logger.info("Agent stopped.")


if __name__ == "__main__":
  main()