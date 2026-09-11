import io
import logging
import os

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.shared import Inches, Pt, RGBColor

logger = logging.getLogger(__name__)

ACCENT = RGBColor(0x1A, 0x4F, 0x8B)
SUBTLE = RGBColor(0x66, 0x66, 0x66)


def _add_heading(doc, text, level):
  heading = doc.add_heading(text, level=min(max(level, 0), 4))
  for run in heading.runs:
    run.font.color.rgb = ACCENT
  return heading


def _add_paragraph(doc, text):
  return doc.add_paragraph(text)


def _add_list(doc, items, numbered):
  for item in items:
    if numbered:
      doc.add_paragraph(item, style="List Number")
    else:
      doc.add_paragraph(item, style="List Bullet")


def _add_table(doc, headers, rows):
  if not headers:
    return
  table = doc.add_table(rows=1, cols=len(headers))
  table.style = "Light Grid Accent 1"
  table.alignment = WD_TABLE_ALIGNMENT.CENTER
  hdr = table.rows[0].cells
  for i, h in enumerate(headers):
    hdr[i].text = str(h)
    for p in hdr[i].paragraphs:
      for run in p.runs:
        run.font.bold = True
  for row in rows:
    cells = table.add_row().cells
    for i, val in enumerate(row):
      if i < len(cells):
        cells[i].text = str(val)


def generate_docx(title, elements, output_path=None):
  """Build a Word document from a list of structured elements.

  elements is a list of dicts, each with a 'type' key:
    {"type": "heading", "text": "...", "level": 1}
    {"type": "paragraph", "text": "..."}
    {"type": "numbered_list", "items": [...]}
    {"type": "bulleted_list", "items": [...]}
    {"type": "table", "headers": [...], "rows": [[...], ...]}
  Returns bytes; writes to output_path if given.
  """
  doc = Document()

  title_p = doc.add_heading(title, level=0)
  for run in title_p.runs:
    run.font.color.rgb = ACCENT

  for el in elements or []:
    el_type = el.get("type", "paragraph")
    try:
      if el_type == "heading":
        _add_heading(doc, el.get("text", ""), el.get("level", 1))
      elif el_type == "paragraph":
        _add_paragraph(doc, el.get("text", ""))
      elif el_type == "numbered_list":
        _add_list(doc, el.get("items", []), numbered=True)
      elif el_type == "bulleted_list":
        _add_list(doc, el.get("items", []), numbered=False)
      elif el_type == "table":
        _add_table(doc, el.get("headers", []), el.get("rows", []))
      else:
        logger.warning(f"Unknown docx element type: {el_type}")
    except Exception as e:
      logger.warning(f"Failed to render element {el_type}: {e}")

  buf = io.BytesIO()
  doc.save(buf)
  data = buf.getvalue()

  if output_path:
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "wb") as f:
      f.write(data)
    logger.info(f"Saved docx to {output_path} ({len(data)} bytes)")

  logger.info(f"Generated docx: {title} ({len(data)} bytes)")
  return data


def generate_docx_bytes_io(title, elements):
  """Return io.BytesIO for direct upload (no temp file needed)."""
  return io.BytesIO(generate_docx(title, elements))