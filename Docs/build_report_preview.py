import html
import re
import zipfile
from pathlib import Path
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
DOCX_PATH = ROOT / "Docs" / "Wajhati_University_Project_Report.docx"
OUTPUT_HTML = ROOT / "Docs" / "Wajhati_University_Project_Report_preview.html"

W_NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
R_NS = {"r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"}


def paragraph_text(paragraph):
    parts = []
    for node in paragraph.findall(".//w:t", W_NS):
        parts.append(node.text or "")
    return "".join(parts).strip()


def paragraph_is_heading(paragraph):
    style = paragraph.find("./w:pPr/w:pStyle", W_NS)
    if style is None:
        return None
    value = style.attrib.get(f"{{{W_NS['w']}}}val", "")
    return value if value.startswith("Heading") else None


def paragraph_images(paragraph, relationships):
    images = []
    for blip in paragraph.findall(".//{http://schemas.openxmlformats.org/drawingml/2006/main}blip"):
        rel_id = blip.attrib.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed")
        if rel_id and rel_id in relationships:
            target = relationships[rel_id]
            if target.startswith("media/"):
                images.append(f"./{html.escape(target)}")
    return images


def load_relationships(docx_path):
    with zipfile.ZipFile(docx_path) as zf:
        root = ET.fromstring(zf.read("word/_rels/document.xml.rels"))
    rels = {}
    for rel in root:
        rel_id = rel.attrib.get("Id")
        target = rel.attrib.get("Target")
        if rel_id and target:
            rels[rel_id] = target
    return rels


def build_html():
    relationships = load_relationships(DOCX_PATH)
    with zipfile.ZipFile(DOCX_PATH) as zf:
        document = ET.fromstring(zf.read("word/document.xml"))

    body = []
    image_count = 0
    for paragraph in document.findall(".//w:body/w:p", W_NS):
        heading_style = paragraph_is_heading(paragraph)
        text = paragraph_text(paragraph)
        images = paragraph_images(paragraph, relationships)

        for image in images:
            image_count += 1
            media_src = image.replace("./media/", "./docx_media/")
            body.append(f'<figure class="figure"><img src="{media_src}" alt="Figure {image_count}"></figure>')

        if not text:
            continue

        escaped = html.escape(text)
        if heading_style == "Heading1":
            if re.fullmatch(r"Chapter \d+", text):
                body.append(f'<section class="chapter-page"><div><div class="chapter-kicker">{escaped}</div></div></section>')
            else:
                body.append(f"<h1>{escaped}</h1>")
        elif heading_style == "Heading2":
            body.append(f"<h2>{escaped}</h2>")
        elif heading_style == "Heading3":
            body.append(f"<h3>{escaped}</h3>")
        else:
            if text.startswith("Figure ") or text.startswith("Table "):
                body.append(f'<p class="caption">{escaped}</p>')
            else:
                body.append(f"<p>{escaped}</p>")

    html_doc = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Wajhati University Project Report Preview</title>
  <style>
    :root {{
      --ink: #1f2933;
      --accent: #123b5d;
      --muted: #6b7280;
      --paper: #fffdf9;
      --line: #d7dee7;
    }}
    body {{
      margin: 0;
      background: #eef2f6;
      color: var(--ink);
      font-family: "Times New Roman", serif;
      line-height: 1.7;
    }}
    .wrap {{
      max-width: 900px;
      margin: 0 auto;
      background: var(--paper);
      min-height: 100vh;
      padding: 48px 64px 72px;
      box-shadow: 0 12px 40px rgba(18, 59, 93, 0.08);
    }}
    h1, h2, h3 {{
      color: var(--accent);
      margin-top: 2rem;
      margin-bottom: 0.75rem;
      line-height: 1.25;
    }}
    h1 {{
      text-align: center;
      font-size: 2rem;
      border-bottom: 1px solid var(--line);
      padding-bottom: 0.35rem;
    }}
    h2 {{ font-size: 1.35rem; }}
    h3 {{ font-size: 1.12rem; }}
    p {{
      margin: 0 0 1rem;
      text-align: justify;
    }}
    .caption {{
      text-align: center;
      font-style: italic;
      color: var(--muted);
      margin-top: 0.5rem;
    }}
    .figure {{
      margin: 1.2rem 0;
      text-align: center;
    }}
    .figure img {{
      max-width: 100%;
      height: auto;
      border: 1px solid var(--line);
      background: white;
    }}
    .chapter-page {{
      min-height: 60vh;
      display: flex;
      align-items: center;
      justify-content: center;
      text-align: center;
      page-break-before: always;
    }}
    .chapter-kicker {{
      font-size: 2.2rem;
      color: var(--accent);
      font-weight: 700;
      letter-spacing: 0.03em;
    }}
    .top-links {{
      position: sticky;
      top: 0;
      background: rgba(255,253,249,0.95);
      backdrop-filter: blur(8px);
      border-bottom: 1px solid var(--line);
      padding: 12px 0;
      margin: -48px -64px 24px;
      text-align: center;
      z-index: 10;
    }}
    .top-links a {{
      color: var(--accent);
      text-decoration: none;
      margin: 0 10px;
      font-weight: 700;
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="top-links">
      <a href="./Wajhati_University_Project_Report.docx">Download Word File</a>
    </div>
    {''.join(body)}
  </div>
</body>
</html>
"""
    OUTPUT_HTML.write_text(html_doc, encoding="utf-8")

    media_target = ROOT / "Docs" / "docx_media"
    media_target.mkdir(exist_ok=True)
    with zipfile.ZipFile(DOCX_PATH) as zf:
        for name in zf.namelist():
            if name.startswith("word/media/"):
                output = media_target / Path(name).name
                output.write_bytes(zf.read(name))


if __name__ == "__main__":
    build_html()
