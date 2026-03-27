import re
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_DOCX = ROOT / "Project Report Sample.docx"
DEFAULT_SOURCE_MD = ROOT / "Docs" / "applied_project_report_sample_aligned.md"
DEFAULT_OUTPUT_DOCX = ROOT / "Project Report Wajhati Sample Aligned.docx"

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def para_xml(text="", *, bold=False, center=False, style=None, preserve_space=False):
    escaped = escape(text)
    ppr = []
    if style:
        ppr.append(f'<w:pStyle w:val="{style}"/>')
    if center:
        ppr.append('<w:jc w:val="center"/>')
    ppr_xml = f"<w:pPr>{''.join(ppr)}</w:pPr>" if ppr else ""
    if text == "":
        return f"<w:p>{ppr_xml}</w:p>"
    rpr = "<w:rPr><w:b/></w:rPr>" if bold else ""
    space_attr = ' xml:space="preserve"' if preserve_space or text.strip() != text else ""
    return f"<w:p>{ppr_xml}<w:r>{rpr}<w:t{space_attr}>{escaped}</w:t></w:r></w:p>"


def code_para_xml(text):
    escaped = escape(text)
    return (
        "<w:p><w:pPr><w:pStyle w:val=\"NoSpacing\"/></w:pPr>"
        "<w:r><w:rPr><w:rFonts w:ascii=\"Courier New\" w:hAnsi=\"Courier New\"/>"
        "<w:sz w:val=\"20\"/></w:rPr>"
        f"<w:t xml:space=\"preserve\">{escaped}</w:t></w:r></w:p>"
    )


def table_xml(rows):
    tbl_pr = (
        "<w:tblPr>"
        "<w:tblStyle w:val=\"TableGrid\"/>"
        "<w:tblW w:w=\"0\" w:type=\"auto\"/>"
        "<w:tblBorders>"
        "<w:top w:val=\"single\" w:sz=\"8\" w:space=\"0\" w:color=\"000000\"/>"
        "<w:left w:val=\"single\" w:sz=\"8\" w:space=\"0\" w:color=\"000000\"/>"
        "<w:bottom w:val=\"single\" w:sz=\"8\" w:space=\"0\" w:color=\"000000\"/>"
        "<w:right w:val=\"single\" w:sz=\"8\" w:space=\"0\" w:color=\"000000\"/>"
        "<w:insideH w:val=\"single\" w:sz=\"8\" w:space=\"0\" w:color=\"000000\"/>"
        "<w:insideV w:val=\"single\" w:sz=\"8\" w:space=\"0\" w:color=\"000000\"/>"
        "</w:tblBorders>"
        "</w:tblPr>"
    )
    grid_cols = len(rows[0]) if rows else 0
    tbl_grid = "<w:tblGrid>" + "".join("<w:gridCol w:w=\"2400\"/>" for _ in range(grid_cols)) + "</w:tblGrid>"
    tr_xml = []
    for row_index, row in enumerate(rows):
        cells = []
        for cell in row:
            text = escape(cell)
            rpr = "<w:rPr><w:b/></w:rPr>" if row_index == 0 else ""
            cells.append(
                "<w:tc>"
                "<w:tcPr><w:tcW w:w=\"2400\" w:type=\"dxa\"/></w:tcPr>"
                f"<w:p><w:r>{rpr}<w:t>{text}</w:t></w:r></w:p>"
                "</w:tc>"
            )
        tr_xml.append("<w:tr>" + "".join(cells) + "</w:tr>")
    return "<w:tbl>" + tbl_pr + tbl_grid + "".join(tr_xml) + "</w:tbl>"


def is_table_line(line):
    stripped = line.strip()
    return stripped.startswith("|") and stripped.endswith("|")


def parse_table(lines, start):
    rows = []
    index = start
    while index < len(lines) and is_table_line(lines[index]):
        parts = [part.strip() for part in lines[index].strip().strip("|").split("|")]
        rows.append(parts)
        index += 1
    if len(rows) >= 2 and all(set(cell) <= {"-"} for cell in rows[1]):
        rows.pop(1)
    return rows, index


def build_document_body(markdown_text):
    lines = markdown_text.splitlines()
    body = []
    index = 0
    in_code = False

    while index < len(lines):
        raw_line = lines[index]
        line = raw_line.rstrip("\n")
        stripped = line.strip()

        if stripped.startswith("```"):
            in_code = not in_code
            index += 1
            continue

        if in_code:
            body.append(code_para_xml(line))
            index += 1
            continue

        if is_table_line(line):
            rows, index = parse_table(lines, index)
            if rows:
                body.append(table_xml(rows))
            continue

        if stripped == "---":
            body.append(para_xml())
            index += 1
            continue

        if not stripped:
            body.append(para_xml())
            index += 1
            continue

        if stripped.startswith("# "):
            body.append(para_xml(stripped[2:].strip(), bold=True, center=True, style="Heading1"))
        elif stripped.startswith("## "):
            body.append(para_xml(stripped[3:].strip(), bold=True, style="Heading2"))
        elif stripped.startswith("### "):
            body.append(para_xml(stripped[4:].strip(), bold=True, style="Heading3"))
        elif stripped.startswith("#### "):
            body.append(para_xml(stripped[5:].strip(), bold=True))
        else:
            body.append(para_xml(line, preserve_space=True))
        index += 1

    return "".join(body)


def main():
    source_md = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_SOURCE_MD
    output_docx = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_OUTPUT_DOCX

    markdown_text = source_md.read_text(encoding="utf-8")
    body_xml = build_document_body(markdown_text)
    document_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:document xmlns:w="{W_NS}">'
        f"<w:body>{body_xml}<w:sectPr><w:pgSz w:w=\"12240\" w:h=\"15840\"/>"
        "<w:pgMar w:top=\"1440\" w:right=\"1440\" w:bottom=\"1440\" w:left=\"1440\" "
        "w:header=\"708\" w:footer=\"708\" w:gutter=\"0\"/></w:sectPr></w:body></w:document>"
    )

    with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
        temp_path = Path(tmp.name)

    with zipfile.ZipFile(TEMPLATE_DOCX, "r") as source, zipfile.ZipFile(temp_path, "w") as target:
        for item in source.infolist():
            if item.filename == "word/document.xml":
                continue
            target.writestr(item, source.read(item.filename))
        target.writestr("word/document.xml", document_xml)

    shutil.move(str(temp_path), output_docx)

    print(output_docx)


if __name__ == "__main__":
    main()
