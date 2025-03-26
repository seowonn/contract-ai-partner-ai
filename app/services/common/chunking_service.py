import re
from typing import List

from app.schemas.chunk_schema import ArticleChunk, ClauseChunk, DocumentChunk

MIN_CLAUSE_BODY_LENGTH = 5

def split_text_by_pattern(text: str, pattern: str) -> List[str]:
  return re.split(pattern, text)


# def chunk_by_article_and_clause_with_page(extracted_text: list) -> List[
#   ArticleChunk]:
#   result: List[ArticleChunk] = []
#   previous_last_sentence = ""  # 이전 페이지에서 잘린 문장을 저장할 변수
#
#   for page, page_text in extracted_text:
#     sentence_index = 1  # 각 페이지마다 문장 번호를 1로 초기화
#
#     page_text = previous_last_sentence + page_text  # 이전 페이지에서 잘린 문장을 현재 페이지에 이어 붙임
#     previous_last_sentence = ""  # 이어 붙였으므로 초기화
#
#     # 1. 페이지 텍스트를 조항별로 분리
#     chunks = split_text_by_pattern(page_text, r'\n(제\s*\d+조(?:\([^)]+\))?)')
#
#     # 2. 각 조항을 청킹
#     for i in range(1, len(chunks), 2):
#       article_title = chunks[i].strip()
#       article_body = chunks[i + 1].strip() if i + 1 < len(chunks) else ""
#
#       # 조항 내의 \n을 제거
#       article_title = article_title.replace('\n', ' ')
#       article_body = article_body.replace('\n', ' ')
#
#       clauses = []
#
#       # 3. 항의 시작을 ① 또는 1.로 정의 (기준문서에서만 해당)
#       first_clause_match = re.search(r'(①|1\.)', article_body)
#       if first_clause_match is None:
#         # 항이 없으면 조항 내용만 저장하고, 해당 페이지를 기록
#         result.append(
#             ArticleChunk(article_title=article_title + article_body, clauses=[],
#                          page=page, sentence_index=sentence_index))
#         sentence_index += 1
#         continue
#
#       # 4. 항의 시작 위치 계산
#       match_idx = first_clause_match.start()
#       article_title += ' ' + article_body[:match_idx]
#
#       if first_clause_match:
#         clause_pattern = r'([\n\s]*[①-⑨])' if first_clause_match.group(
#           1) == '①' else r'(\n\s*\d+\.)'
#         clause_chunks = split_text_by_pattern("\n" + article_body[match_idx:],
#                                               clause_pattern)
#
#         # 5. 항들을 청킹하여 추가
#         for j in range(1, len(clause_chunks), 2):
#           clause_title = clause_chunks[j].strip()
#           clause_body = clause_chunks[j + 1].strip() if j + 1 < len(
#             clause_chunks) else ""
#
#           if len(clause_body) >= MIN_CLAUSE_BODY_LENGTH:
#             clauses.append(ClauseChunk(clause_number=clause_title,
#                                        clause_content=clause_body))
#
#       # 6. 페이지 번호를 포함하여 ArticleChunk 저장
#       if page == 1:  # 첫 번째 페이지에서만 문장 저장
#         result.append(
#             ArticleChunk(article_title=article_title, clauses=clauses,
#                          page=page, sentence_index=sentence_index))
#         sentence_index += 1  # 문장 번호 증가
#
#     # 7. 만약 문장이 잘렸다면 이어서 처리 (현재 페이지의 텍스트에서 이어서 처리)
#     if sentence_index == 1:
#       previous_last_sentence = chunks[-1]  # 문장이 잘린 경우, 이어서 저장할 마지막 문장을 추출
#     print(result)  # 결과 확인
#     # 8. 최종 결과 반환
#     return result

def chunk_by_article_and_clause_with_page(extracted_text: list) -> List[
  DocumentChunk]:
  result: List[DocumentChunk] = []
  previous_last_sentence = ""  # 이전 페이지에서 잘린 문장을 저장할 변수

  for page, page_text in extracted_text:
    sentence_index = 1  # 문장 번호 초기화
    # print(f'붙여야하는 문장==========={previous_last_sentence}')
    # page_text = previous_last_sentence + page_text  # 이전 페이지에서 잘린 문장을 이어 붙임
    # print(f'붙인 문장==========={page_text}')
    # 1. '제X조'를 기준으로 텍스트를 분리
    pattern = r'(제\d+조\s*【[^】]+】)(.*?)(?=(제\d+조|$))'  # 제X조를 기준으로 분리
    matches = re.findall(pattern, page_text, flags=re.DOTALL)


    # if previous_last_sentence:
    #   if matches:
    #     # 첫 번째 항목인 제X조 앞부분에 previous_last_sentence를 결합
    #     matches[0] = previous_last_sentence + matches[0][1]
    #     previous_last_sentence = ""  # 잘린 문장은 처리되었으므로 초기화
    #     print(f'matches========={matches}')

    # matches : 페이지
    # article_body : 조
    # 2. 각 조항을 청킹
    for match in matches:
      article_body = match[1].strip()  # 조 내용
      print(f'article_body=========={article_body}')
      # 3. 항목 번호가 있는 경우 번호와 내용으로 분리
      clause_pattern = r'([①-⑨]|\d+\.)\s*([^\①②③④⑤⑥⑦⑧⑨\d\.\n]+(?:\n[^\①②③④⑤⑥⑦⑧⑨\d\.\n]+)*)'
      clause_matches = re.findall(clause_pattern, article_body)
      print(f"clause_matches=============: {clause_matches}")

      # 4. 번호가 있는 경우, 항목 번호별로 청킹 추가
      if clause_matches:
        for clause in clause_matches:
          clause_number = clause[0]  # 항목 번호 (①, 1., 2., 등)
          clause_content = clause[1].strip()  # 항목 내용

          if len(clause_content) >= 10 and clause_content.endswith(
              '.'):  # 최소 10자 이상의 내용만 추가
            result.append(DocumentChunk(clauses=clause_content, page=page,
                                        sentence_index=sentence_index))
            sentence_index += 1  # 문장 번호 증가
      else:
        # 번호가 없으면, 전체 문장을 하나의 항목으로 처리
        if article_body.endswith('.'):
          result.append(DocumentChunk(clauses=article_body, page=page,
                                      sentence_index=sentence_index))
          sentence_index += 1  # 문장 번호 증가

    # # 5. 문장이 잘렸다면 이어서 처리
    # last_line = page_text.split("\n")[-1]  # 마지막 줄 추출
    #
    # # 문장이 잘렸는지 확인 (구두점이 없으면 문장이 잘린 것)
    # if not last_line.endswith(('.', '?', '!', '。', '！', '？')):
    #   previous_last_sentence = last_line  # 문장이 잘린 경우, 마지막 문장 저장
    #   # print(f'잘린문장==========={previous_last_sentence}')
    # else:
    #   previous_last_sentence = ""  # 문장이 정상적으로 끝났으면 초기화

  # print(result)
  return result

