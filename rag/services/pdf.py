import logging

import pdfplumber

logger = logging.getLogger(__name__)


def process_difficult_pdf(pdf_path):
    pdf_text = ""
    pdf_pages = 0
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):

            pdf_pages = len(pdf.pages)
            logger.debug("Processing page %s/%s", page_num, pdf_pages)

            # 1. Extract structured tables found on the page
            tables = page.extract_tables()
            text_tables = ""
            if tables:
                for table in tables:
                    for row in table:
                        # Clean up None values or line breaks inside cells
                        clean_row = [str(cell).replace('\n', ' ') if cell else "" for cell in row]
                        text_tables += " ".join(" | ".join(clean_row).split())

            pdf_text += text_tables
            # 2. Extract regular text with layout preservation settings
            # layout=True helps maintain vertical alignment and structural reading order
            text = page.extract_text(layout=True)
            if text:
                pdf_text += " ".join(text.split())

        return pdf_pages, pdf_text

