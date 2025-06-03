import re
from typing import List, Tuple

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.blueprints.agreement.agreement_exception import AgreementException
from app.common.constants import ARTICLE_CLAUSE_SEPARATOR, CLAUSE_HEADER_PATTERN
from app.common.exception.custom_exception import CommonException
from app.common.exception.error_code import ErrorCode
from app.schemas.chunk_schema import Document, DocumentChunk
from app.services.agreement.mapping import HEADER_PARSERS, CHUNKING_STRATEGIES
from app.services.common.chunking_service import \
  split_by_clause_header_pattern, \
  MIN_CLAUSE_BODY_LENGTH, check_if_preamble_exists_except_first_page, \
  chunk_preamble_content


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


def chunk_by_article_and_clause_with_page(documents: List[Document],
    pattern: str) -> List[
  DocumentChunk]:
  chunks: List[DocumentChunk] = []

  for doc in documents:
    page = doc.metadata.page
    page_text = doc.page_content
    order_index = 1

    preamble_exists = check_if_preamble_exists_except_first_page(pattern,
                                                                 page_text)
    if preamble_exists:
      order_index, chunks = (
        chunk_preamble_content(pattern, page_text, chunks, page, order_index))

    matches = re.findall(pattern, page_text, flags=re.DOTALL)
    header_parser = HEADER_PARSERS.get(pattern)

    for header, body in matches:
      if not header_parser:
        continue

      header_match = header_parser(header)
      if not header_match:
        continue

      article_number, article_title = header_match
      article_body = body.strip()

      first_clause_match = re.search(CLAUSE_HEADER_PATTERN, article_body)
      if first_clause_match and article_body.startswith(
          first_clause_match.group(1)):

        clause_chunks = (
          split_by_clause_header_pattern(
              first_clause_match.group(1), "\n" + article_body))

        for j in range(1, len(clause_chunks), 2):
          clause_number = clause_chunks[j].strip()
          if clause_number.endswith("."):
            clause_number = clause_number[:-1]

          clause_content = clause_chunks[j + 1].strip() if j + 1 < len(
              clause_chunks) else ""

          if len(clause_content) >= MIN_CLAUSE_BODY_LENGTH:
            chunks.append(DocumentChunk(
                clause_content=f"{article_title}{ARTICLE_CLAUSE_SEPARATOR}\n{clause_content}",
                page=page,
                order_index=order_index,
                clause_number=f"제{article_number}조 {clause_number}항"
            ))
            order_index += 1
      else:
        if len(article_body) >= MIN_CLAUSE_BODY_LENGTH:
          chunks.append(DocumentChunk(
              clause_content=f"{article_title}{ARTICLE_CLAUSE_SEPARATOR}\n{article_body}",
              page=page,
              order_index=order_index,
              clause_number=f"제{article_number}조 1항"
          ))
          order_index += 1

  return chunks


def parse_article_header(header: str) -> Tuple[int, str]:
  clean_header = header.replace(" ", "")

  if not clean_header.startswith("제") or "조" not in clean_header:
    raise AgreementException(ErrorCode.NOT_SUPPORTED_FORMAT)

  try:
    num_part = clean_header.split("조")[0].replace("제", "")
    title_part = clean_header.split("조")[1]
    title_without_parentheses = title_part.strip("【】()[]")
    return int(num_part), title_without_parentheses

  except Exception:
    raise AgreementException(ErrorCode.NOT_SUPPORTED_FORMAT)


def parse_number_header(header: str) -> Tuple[int, str]:
  clean_header = header.replace(" ", "")

  try:
    num_part = clean_header.split(".")[0]
    title_part = clean_header.split(".")[1]
    title_without_parentheses = title_part.strip("【】()[]")
    return int(num_part), title_without_parentheses

  except Exception:
    raise AgreementException(ErrorCode.NOT_SUPPORTED_FORMAT)


def chunk_by_paragraph(documents: List[Document]) -> List[DocumentChunk]:
  chunks = []
  text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
      chunk_size=300,
      chunk_overlap=50,
      separators=["\n\n", "."]
  )

  for doc in documents:
    divided_text = text_splitter.split_text(doc.page_content)

    for idx, content in enumerate(divided_text, start=1):
      chunks.append(
          DocumentChunk(
              page=doc.metadata.page,
              clause_content=content,
              order_index=idx,
              clause_number=str(len(chunks) + 1)
          )
      )

  return chunks
