import re
from typing import List, Tuple, Callable

from app.common.constants import ARTICLE_CHUNK_PATTERN, NUMBER_HEADER_PATTERN
from app.common.exception.custom_exception import CommonException
from app.common.exception.error_code import ErrorCode
from app.schemas.chunk_schema import Document, DocumentChunk
from app.services.common.chunking_service import \
  chunk_by_article_and_clause_with_page, chunk_by_paragraph


CHUNKING_STRATEGIES: List[Tuple[str, Callable]] = [
    (ARTICLE_CHUNK_PATTERN, chunk_by_article_and_clause_with_page),
    (NUMBER_HEADER_PATTERN, chunk_by_article_and_clause_with_page)
]

def chunk_agreement_documents(documents: List[Document]) -> List[DocumentChunk]:
  first_page = documents[0].page_content

  for pattern, chunk_fn in CHUNKING_STRATEGIES:
    if re.findall(pattern, first_page, flags=re.DOTALL):
      chunks = chunk_fn(documents, pattern)
      break

  else:
    chunks = chunk_by_paragraph(documents)

  if not chunks:
    raise CommonException(ErrorCode.CHUNKING_FAIL)

  return chunks
