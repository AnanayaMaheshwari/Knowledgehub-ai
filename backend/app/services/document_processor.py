
from io import BytesIO

import pymupdf
from docx import Document


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """
    Extract text from all pages of a PDF file.
    """
    extracted_pages = []

    try:
        pdf = pymupdf.open(
    stream=file_bytes,
    filetype="pdf"
)

        for page_number, page in enumerate(pdf, start=1):
            page_text = page.get_text("text").strip()

            if page_text:
                extracted_pages.append(
                    f"[Page {page_number}]\n{page_text}"
                )

        pdf.close()

        return "\n\n".join(extracted_pages)

    except Exception as error:
        raise ValueError(
            f"Could not extract text from PDF: {error}"
        )


def extract_text_from_docx(file_bytes: bytes) -> str:
    """
    Extract text from paragraphs and tables in a DOCX file.
    """
    try:
        document = Document(BytesIO(file_bytes))

        extracted_content = []

        # Extract paragraphs
        for paragraph in document.paragraphs:
            text = paragraph.text.strip()

            if text:
                extracted_content.append(text)

        # Extract tables
        for table in document.tables:
            for row in table.rows:
                row_data = [
                    cell.text.strip()
                    for cell in row.cells
                ]

                extracted_content.append(
                    " | ".join(row_data)
                )

        return "\n".join(extracted_content)

    except Exception as error:
        raise ValueError(
            f"Could not extract text from DOCX: {error}"
        )


def extract_document_text(
    file_bytes: bytes,
    file_type: str
) -> str:
    """
    Select the appropriate extraction method.
    """

    file_type = file_type.lower().replace(".", "")

    if file_type == "pdf":
        return extract_text_from_pdf(file_bytes)

    elif file_type == "docx":
        return extract_text_from_docx(file_bytes)

    else:
        raise ValueError(
            "Unsupported file type. Only PDF and DOCX are supported."
        )
