import re
from typing import List

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.common.constants import ARTICLE_CLAUSE_SEPARATOR, CLAUSE_HEADER_PATTERN
from app.common.exception.custom_exception import CommonException
from app.common.exception.error_code import ErrorCode
from app.schemas.chunk_schema import Document, DocumentChunk
from app.services.agreement.chunk_regex import CHUNKING_REGEX, ARTICLE_NUMBER
from app.services.common.chunking_service import \
  split_by_clause_header_pattern, \
  MIN_CLAUSE_BODY_LENGTH, check_if_preamble_exists_except_first_page, \
  chunk_preamble_content


def chunk_agreement_documents(documents: List[Document]) -> List[DocumentChunk]:
  first_page = documents[0].page_content

  for strategy in CHUNKING_REGEX:
    if re.findall(strategy["regex"], first_page, flags=re.DOTALL):
      chunks = chunk_by_article_and_clause_with_page(documents, strategy)
      break
  else:
    chunks = chunk_by_paragraph(documents)

  if not chunks:
    raise CommonException(ErrorCode.CHUNKING_FAIL)

  return chunks


def chunk_by_article_and_clause_with_page(documents: List[Document],
    strategy: dict) -> List[DocumentChunk]:
  pattern = strategy["regex"]
  chunks: List[DocumentChunk] = []

  for doc in documents:
    page, text = doc.metadata.page, doc.page_content
    order_index = 1

    if check_if_preamble_exists_except_first_page(pattern,text):
      order_index, chunks = (
        chunk_preamble_content(pattern, text, chunks, page, order_index))

    matches = re.findall(pattern, text, flags=re.DOTALL)

    # 회사 계약서는 굳이 조 번호 / 제목으로 구분하지 않아도 된다고 해서 matches를 그대로 사용
    for body in matches:
      article_body = body.strip()
      article_number = ""

      for _, form in ARTICLE_NUMBER.items():
        if re.findall(form, article_body, flags=re.DOTALL):
          article_number = re.findall(form, article_body)
          break

      first_clause_match = re.search(CLAUSE_HEADER_PATTERN, article_body)
      if first_clause_match and article_body.startswith(
          first_clause_match.group(1)):

        clause_chunks = (
          split_by_clause_header_pattern(
              first_clause_match.group(1), "\n" + article_body))

        for j in range(1, len(clause_chunks), 2):
          clause_content = clause_chunks[j + 1].strip() if j + 1 < len(
              clause_chunks) else ""

          if len(clause_content) >= MIN_CLAUSE_BODY_LENGTH:
            chunks.append(DocumentChunk(
                clause_content=f"{ARTICLE_CLAUSE_SEPARATOR}\n{clause_content}",
                page=page,
                order_index=order_index,
                clause_number=f"{article_number}조"
            ))
            order_index += 1
      else:
        if len(article_body) >= MIN_CLAUSE_BODY_LENGTH:
          chunks.append(DocumentChunk(
              clause_content=f"{ARTICLE_CLAUSE_SEPARATOR}\n{article_body}",
              page=page,
              order_index=order_index,
              clause_number=f"{article_number}조"
          ))
          order_index += 1

  chunks[-1].clause_content = chunks[-1].clause_content.split("     ")[0]
  return chunks


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
