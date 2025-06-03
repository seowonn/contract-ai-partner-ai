from typing import List

import fitz

from app.common.exception.custom_exception import CommonException
from app.common.exception.error_code import ErrorCode
from app.schemas.chunk_schema import Document, DocumentMetadata


def parse_standard_pdf_to_documents(doc: fitz.Document) -> List[Document]:
  documents: List[Document] = []

  try:
    for page in doc:
      blocks = page.get_text("blocks")
      page_number = page.number + 1

      for block in blocks:
        x0, y0, x1, y1, text, *_ = block
        text = text.strip()
        if not text:
          continue

        block_type = "table" if "\t" in text or "│" in text else "text"

        meta = DocumentMetadata(
          page=page_number,
          bbox=(x0, y0, x1, y1),
          type=block_type
        )
        documents.append(Document(
          page_content=text,
          metadata=meta
        ))

  except Exception:
    raise CommonException(ErrorCode.PDF_LOAD_FAILED)

  if not documents:
    raise CommonException(ErrorCode.NO_TEXTS_EXTRACTED)

  return documents
