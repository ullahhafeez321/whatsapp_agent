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
deploy/         Oracle Cloud Always Free installer + systemd service
```

## Free 24/7 hosting (Oracle Cloud Always Free)

The agent long-polls the WhatsApp gateway, so it must run on an always-on
server — a free host that sleeps on idle (Render, Glitch, Replit) will not
work. Oracle Cloud's **Always Free** VM tier is a good fit: two micro VMs
forever, no cost, never sleeps. No Docker needed.

### 1. Create the VM

1. Sign up at <https://www.oracle.com/cloud/free/>
2. Create a **Compute → Instance** with shape **VM.Standard.A1.Flex** (ARM,
   always free) or **VM.Standard.E2.1.Micro** (AMD, always free). 1 OCPU +
   1 GB RAM is plenty.
3. Use an **Ubuntu 22.04/24.04** image.
4. **Important:** add your SSH public key during instance creation so you can
   log in. Ensure the default security list keeps **port 22 open**.
5. After creation, note the public IP.

### 2. Run the installer

```bash
ssh ubuntu@<your-vm-public-ip>

# One-liner: download and run the installer, passed your keys:
sudo GEMINI_API_KEY=your_gemini_key WHATSAPP_API_TOKEN=your_token \
  bash -c "$(curl -fsSL https://raw.githubusercontent.com/ullahhafeez321/whatsapp_agent/main/deploy/install.sh)"
```

Or clone manually and edit keys first:

```bash
git clone https://github.com/ullahhafeez321/whatsapp_agent.git
cd whatsapp_agent
nano .env          # paste GEMINI_API_KEY and WHATSAPP_API_TOKEN
sudo bash deploy/install.sh
```

### 3. Daily use

```bash
sudo systemctl status whatsapp-agent     # status
sudo journalctl -u whatsapp-agent -f     # live logs
sudo systemctl restart whatsapp-agent    # restart
```

The service restarts automatically if the process crashes, and starts on boot.
The VM only needs outbound internet — no inbound ports beyond SSH.

## License

For educational use. Respect WhatsApp's Terms of Service and Google's Gemini usage policies.