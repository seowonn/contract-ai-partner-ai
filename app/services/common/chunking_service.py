import re
from typing import List

from app.schemas.chunk_schema import ArticleChunk, ClauseChunk

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

  return result  # ✅ 조 + 항 구조 유지한 채 반환
