import re
from typing import List, Tuple

from app.common.constants import ARTICLE_OCR_HEADER_PATTERN, \
  CLAUSE_HEADER_PATTERN, ARTICLE_CLAUSE_SEPARATOR
from app.schemas.chunk_schema import Document, DocumentChunk
from app.services.common.chunking_service import split_by_clause_header_pattern, \
  MIN_CLAUSE_BODY_LENGTH, get_clause_pattern, split_text_by_pattern




def chunk_preamble_content_ocr(page_text: str, chunks: List[DocumentChunk],
    order_index: int) -> Tuple[int, List[DocumentChunk]]:
  first_article_match = (
    re.search(ARTICLE_OCR_HEADER_PATTERN, page_text, flags=re.MULTILINE))

  preamble = page_text[
             first_article_match.start():] if first_article_match else page_text
  return append_preamble_ocr(chunks, preamble, order_index)


def append_preamble_ocr(result: List[DocumentChunk], preamble: str,
    order_index: int) -> Tuple[int, List[DocumentChunk]]:
  pattern = get_clause_pattern(result[-1].clause_number)

  if not pattern:
    result.append(DocumentChunk(
        clause_content=preamble,
        order_index=order_index,
        clause_number=result[-1].clause_number
    ))
    return order_index + 1, result

  clause_chunks = split_text_by_pattern(preamble, pattern)
  lines = clause_chunks[0].strip().splitlines()
  content_lines = [line for line in lines if not line.strip().startswith("페이지")]

  result.append(DocumentChunk(
      clause_content="\n".join(content_lines),
      order_index=order_index,
      clause_number=result[-1].clause_number
  ))
  order_index += 1

  for j in range(1, len(clause_chunks), 2):
    clause_number = clause_chunks[j].strip()
    clause_content = clause_chunks[j + 1].strip() if j + 1 < len(
        clause_chunks) else ""

    if len(clause_content) >= MIN_CLAUSE_BODY_LENGTH:
      prev_clause_prefix = result[-1].clause_number.split(" ")[0]
      result.append(DocumentChunk(
          clause_content=clause_content,
          order_index=order_index,
          clause_number=f"{prev_clause_prefix} {clause_number}항"
      ))
      order_index += 1

  return order_index, result