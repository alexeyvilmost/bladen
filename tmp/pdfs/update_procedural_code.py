from pathlib import Path

import fitz


ROOT = Path(r"C:\Users\Алексей\Documents\Lazy DM System")
SOURCE = ROOT / "output" / "pdf" / "Процессуальный кодекс Бладена.pdf"
OUTPUT = ROOT / "tmp" / "pdfs" / "Процессуальный кодекс Бладена.updated.pdf"


document = fitz.open(SOURCE)
if document.page_count != 10:
    raise RuntimeError(f"Expected 10 source pages, found {document.page_count}")

title_page = document[0]
definition_start = title_page.search_for("Кровная подпись")
definition_end = title_page.search_for("Тирану.")
if len(definition_start) != 1 or len(definition_end) != 1:
    raise RuntimeError("Definition paragraph was not found uniquely on the title page")

definition_area = fitz.Rect(
    50,
    definition_start[0].y0 - 4,
    title_page.rect.width - 50,
    definition_end[0].y1 + 4,
)
title_page.add_redact_annot(definition_area, fill=(1, 1, 1))
title_page.apply_redactions()

# The public edition is printed with a blank first leaf; the title begins on page two.
document.insert_page(0, width=fitz.paper_rect("a4").width, height=fitz.paper_rect("a4").height)
document.save(OUTPUT, garbage=4, deflate=True)
document.close()

check = fitz.open(OUTPUT)
if check.page_count != 11:
    raise RuntimeError(f"Expected 11 output pages, found {check.page_count}")
if check[0].get_text().strip():
    raise RuntimeError("Inserted first page is not blank")
if not check[1].search_for("Процессуальный кодекс Бладена"):
    raise RuntimeError("Title is not on the second page")
for forbidden in ("Кровная подпись", "Клов", "Аудиенция"):
    if any(page.search_for(forbidden) for page in check):
        raise RuntimeError(f"Removed definition remains in PDF text layer: {forbidden}")
check.close()
