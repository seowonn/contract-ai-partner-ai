import re
from typing import List

from app.schemas.chunk_schema import ArticleChunk, ClauseChunk, DocumentChunk
from app.schemas.chunk_schema import Document

MIN_CLAUSE_BODY_LENGTH = 5

def split_text_by_pattern(text: str, pattern: str) -> List[str]:
  return re.split(pattern, text)


def chunk_by_article_and_clause(extracted_text: str) -> List[ArticleChunk]:
  article_pattern = r'\n(제\s*\d+조(?:\([^)]+\))?)'  # 조(Article) 기준 정규식

  chunks = split_text_by_pattern(extracted_text, article_pattern)
  result: List[ArticleChunk] = []

  for i in range(1, len(chunks), 2):
    article_title = chunks[i].strip()
    article_body = chunks[i + 1].strip() if i + 1 < len(chunks) else ""

    clauses = []

    # ⭐ 항이 ① 또는 1. 로만 시작한다는 전제 (따라서 기준문서도 이에 맞는 문서만 필요)
    first_clause_match = re.search(r'(①|1\.)', article_body)
    if first_clause_match is None:
      result.append(ArticleChunk(article_title=article_title + article_body, clauses=[]))
      continue

    match_idx = first_clause_match.start()
    article_title += ' ' +article_body[:match_idx]
    if first_clause_match:
      clause_pattern = r'([\n\s]*[①-⑨])' if first_clause_match.group(1) == '①' else r'(\n\s*\d+\.)'
      clause_chunks = split_text_by_pattern("\n" + article_body[match_idx:], clause_pattern)

      for j in range(1, len(clause_chunks), 2):
        clause_title = clause_chunks[j].strip()
        clause_body = clause_chunks[j + 1].strip() if j + 1 < len(clause_chunks) else ""

        if len(clause_body) >= MIN_CLAUSE_BODY_LENGTH:
          clauses.append(ClauseChunk(clause_number=clause_title, clause_content=clause_body))
      result.append(ArticleChunk(article_title=article_title, clauses=clauses))

  return result


def chunk_by_article_and_clause_with_page(extracted_text: list) -> List[
  ArticleChunk]:
  result: List[ArticleChunk] = []

  for page, page_text in extracted_text:
    sentence_index = 1
    # 1. 페이지 텍스트를 조항별로 분리
    chunks = split_text_by_pattern(page_text, r'\n(제\s*\d+조(?:\([^)]+\))?)')

    # 2. 각 조항을 청킹
    for i in range(1, len(chunks), 2):
      article_title = chunks[i].strip()
      article_body = chunks[i + 1].strip() if i + 1 < len(chunks) else ""

      # 조항 내의 \n을 제거
      article_title = article_title.replace('\n', ' ')
      article_body = article_body.replace('\n', ' ')

      clauses = []

      # 3. 항의 시작을 ① 또는 1.로 정의 (기준문서에서만 해당)
      first_clause_match = re.search(r'(①|1\.)', article_body)
      if first_clause_match is None:
        # 항이 없으면 조항 내용만 저장하고, 해당 페이지를 기록
        result.append(
          ArticleChunk(article_title=article_title + article_body, clauses=[],
                       page=page, sentence_index=sentence_index))
        sentence_index += 1
        continue

      # 4. 항의 시작 위치 계산
      match_idx = first_clause_match.start()
      article_title += ' ' + article_body[:match_idx]

      if first_clause_match:
        clause_pattern = r'([\n\s]*[①-⑨])' if first_clause_match.group(
          1) == '①' else r'(\n\s*\d+\.)'
        clause_chunks = split_text_by_pattern("\n" + article_body[match_idx:],
                                              clause_pattern)

        # 5. 항들을 청킹하여 추가
        for j in range(1, len(clause_chunks), 2):
          clause_title = clause_chunks[j].strip()
          clause_body = clause_chunks[j + 1].strip() if j + 1 < len(
            clause_chunks) else ""

          if len(clause_body) >= MIN_CLAUSE_BODY_LENGTH:
            clauses.append(ClauseChunk(clause_number=clause_title,
                                       clause_content=clause_body))

      # 6. 페이지 번호를 포함하여 ArticleChunk 저장
      result.append(ArticleChunk(article_title=article_title, clauses=clauses,
                                 page=page, sentence_index=sentence_index))
      sentence_index += 1

  print(result)
  # 7. 최종 결과 반환
  return result



def chunk_by_article_and_clause_with_page2(documents: List[Document]) -> List[
  DocumentChunk]:
  result: List[DocumentChunk] = []

  for doc in documents:
    sentence_index = 0
    chunks = split_text_by_pattern(doc.page_content, r'\n(제\s*\d+조(?:\([^)]+\))?)')

    for i in range(1, len(chunks), 2):
      article_title = chunks[i].strip()
      article_body = chunks[i + 1].strip() if i + 1 < len(chunks) else ""

      article_title = article_title.replace('\n', ' ')
      article_body = article_body.replace('\n', ' ')

      first_clause_match = re.search(r'(①|1\.)', article_body)
      if first_clause_match is None:
        result.append(
          DocumentChunk(
              clause_content=article_body,
              page=doc.metadata.page,
              order_index=sentence_index,
              clause_number=article_title
          ))
        sentence_index += 1

  return result

