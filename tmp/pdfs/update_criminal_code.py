from pathlib import Path

import fitz


ROOT = Path(r"C:\Users\Алексей\Documents\Lazy DM System")
SOURCE = ROOT / "output" / "pdf" / "Уголовный кодекс Бладена.pdf"
OUTPUT = ROOT / "tmp" / "pdfs" / "Уголовный кодекс Бладена.updated.pdf"
FONT_FILE = Path(
    r"C:\Users\Алексей\.cache\codex-runtimes\codex-primary-runtime"
    r"\dependencies\native\poppler\Library\share\fonts\DejaVuSans.ttf"
)


document = fitz.open(SOURCE)
if document.page_count != 8:
    raise RuntimeError(f"Expected 8 source pages, found {document.page_count}")

body_color = (0.16, 0.14, 0.13)
accent_color = (0.43, 0.04, 0.09)
font_name = "DejaVuSansPatch"

# Article 9: compact statutory note between the severity table and the next paragraph.
severity_page = document[1]
severity_page.insert_text(
    fitz.Point(53.858, 480.0),
    "Для эльфов сроки заключения, указанные для каждой ступени, увеличиваются в семь раз.",
    fontname=font_name,
    fontfile=str(FONT_FILE),
    fontsize=7.5,
    color=accent_color,
    overlay=True,
)

# Article 36: simple evasion rises from degree III to degree IV.
evasion_page = document[5]
degree_three = [
    rect for rect in evasion_page.search_for("III") if 748 < rect.y0 < 766
]
if len(degree_three) != 1:
    raise RuntimeError(f"Expected one Article 36 degree marker, found {degree_three}")
simple_rect = degree_three[0]
evasion_page.add_redact_annot(simple_rect + (-0.7, -0.7, 0.7, 0.7), fill=(1, 1, 1))
evasion_page.apply_redactions()
evasion_page.insert_text(
    fitz.Point(simple_rect.x0, simple_rect.y1 - 0.9),
    "IV",
    fontname=font_name,
    fontfile=str(FONT_FILE),
    fontsize=9,
    color=body_color,
    overlay=True,
)

# Article 37: aggravated evasion rises from degree IV to degree V.
aggravated_page = document[6]
degree_four = [
    rect
    for rect in aggravated_page.search_for("IV ступени, если виновный:")
    if 315 < rect.y0 < 335
]
if len(degree_four) != 1:
    raise RuntimeError(f"Expected one Article 37 degree marker, found {degree_four}")
aggravated_rect = degree_four[0]
aggravated_page.add_redact_annot(
    aggravated_rect + (-0.7, -0.7, 0.7, 0.7), fill=(1, 1, 1)
)
aggravated_page.apply_redactions()
aggravated_page.insert_text(
    fitz.Point(aggravated_rect.x0, aggravated_rect.y1 - 0.9),
    "V ступени, если виновный:",
    fontname=font_name,
    fontfile=str(FONT_FILE),
    fontsize=9,
    color=body_color,
    overlay=True,
)

document.save(OUTPUT, garbage=4, deflate=True)
document.close()

check = fitz.open(OUTPUT)
note = "Для эльфов сроки заключения, указанные для каждой ступени, увеличиваются в семь раз."
if not check[1].search_for(note):
    raise RuntimeError("Elven sentencing note is missing from page 2")
if not [rect for rect in check[5].search_for("IV") if 748 < rect.y0 < 766]:
    raise RuntimeError("Article 36 was not raised to degree IV")
if [rect for rect in check[5].search_for("III") if 748 < rect.y0 < 766]:
    raise RuntimeError("Old Article 36 degree remains in the PDF")
if not [
    rect
    for rect in check[6].search_for("V ступени, если виновный:")
    if 315 < rect.y0 < 335
]:
    raise RuntimeError("Article 37 was not raised to degree V")
if [
    rect
    for rect in check[6].search_for("IV ступени, если виновный:")
    if 315 < rect.y0 < 335
]:
    raise RuntimeError("Old Article 37 degree remains in the PDF")
check.close()
