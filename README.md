# WhatsApp Agent

A smart WhatsApp educational assistant that can chat, generate images, and create Word (.docx) documents — powered by Google Gemini (free tier) and Pollinations.ai.

## Features

- **Conversational AI** — Natural, context-aware chat with full per-user conversation memory (Google Gemini free tier)
- **Image generation** — Ask for diagrams, illustrations, charts; generated via Pollinations.ai (no API key needed)
- **Word document generation** — Create assignments, study guides, reports, and worksheets as professionally styled `.docx` files
- **AI-powered intent detection** — Gemini automatically decides whether a message needs a text answer, an image, or a document
- **Duplicate protection** — Message ID deduplication prevents double-processing
- **Rate-limit aware** — Exponential backoff + retry on transient HTTP errors
- **Conversation session expiry** — Idle sessions auto-clean after 30 minutes

## Requirements

- Python 3.10+
- A free Google Gemini API key from <https://aistudio.google.com/app/apikeys>
- Your WhatsApp agent gateway credentials

## Installation

```bash
pip install -r requirements.txt
cp .env.example .env   # or edit .env directly
```

Edit `.env` and add your keys:

```
GEMINI_API_KEY=your_gemini_api_key_here
WHATSAPP_API_TOKEN=your_gateway_token_here
WHATSAPP_BASE_URL=https://api.whatsapp.com/agent/v1
```

## Usage

```bash
python app.py
```

## Example conversations

| You ask                          | Agent does                              |
| -------------------------------- | --------------------------------------- |
| "What is photosynthesis?"        | Replies with a clear text explanation   |
| "Draw a diagram of a plant cell" | Generates and sends an image            |
| "Make an assignment on the water cycle" | Creates and sends a `.docx` assignment |

## Project structure

```
app.py          Main entry point, polling loop
agent.py        Orchestrator — routes messages, handles tools
llm.py          Google Gemini client + intent detection
whatsapp.py     WhatsApp gateway API client (text/image/document)
image_gen.py    Pollinations.ai image generation
docx_gen.py     Word document generation (python-docx)
config.py       Environment configuration
```

## License

For educational use. Respect WhatsApp's Terms of Service and Google's Gemini usage policies.