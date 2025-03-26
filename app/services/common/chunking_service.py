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
  DocumentChunk]:
  result: List[DocumentChunk] = []


  for page, page_text in extracted_text:
    sentence_index = 1  # 문장 번호 초기화
    # 1. '제X조'를 기준으로 텍스트를 분리
    pattern = r'(제\d+조\s*【[^】]+】)(.*?)(?=(제\d+조|$))'  # 제X조를 기준으로 분리
    matches = re.findall(pattern, page_text, flags=re.DOTALL)

    # 2. 각 조항을 청킹
    for match in matches:
      article_body = match[1].strip()  # 조 내용
      # 3. 항목 번호가 있는 경우 번호와 내용으로 분리
      clause_pattern = r'([①-⑨])\s*([^\①②③④⑤⑥⑦⑧⑨\.\n]+(?:\n(?![①-⑨]|\d+\.)[^\①②③④⑤⑥⑦⑧⑨\.\n]+)*)'
      clause_matches = re.findall(clause_pattern, article_body)

      # 4. 번호가 있는 경우, 항목 번호별로 청킹 추가
      if clause_matches:
        for clause in clause_matches:
          clause_number = clause[0]  # 항목 번호 (①, 1., 2., 등)
          clause_content = clause[1].strip()  # 항목 내용

          if len(clause_content) >= 10:  # 최소 10자 이상의 내용만 추가
            result.append(DocumentChunk(clause_content=clause_content, page=page,
                                        order_index=sentence_index, clause_number=clause_number))
            sentence_index += 1  # 문장 번호 증가
      else:
        # 번호가 없으면, 전체 문장을 하나의 항목으로 처리
        if article_body.endswith('.'):
          result.append(DocumentChunk(clause_content=article_body, page=page,
                                      order_index=sentence_index))
          sentence_index += 1  # 문장 번호 증가

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

