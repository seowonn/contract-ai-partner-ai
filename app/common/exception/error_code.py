from enum import Enum
from http import HTTPStatus


class ErrorCode(Enum):
  # global 에러
  REQUEST_UNMATCH = (HTTPStatus.BAD_REQUEST, "G001", "요청 json 매핑 불일치")
  URL_NOT_FOUND = (HTTPStatus.BAD_REQUEST, "G002", "존재하지 않는 url 요청")

  # standard 관련 에러

  DELETE_FAIL = (HTTPStatus.INTERNAL_SERVER_ERROR, "S002", "삭제 과정 중 에러 발생")
  CHUNKING_FAIL = (HTTPStatus.INTERNAL_SERVER_ERROR, "S003", "청킹된 데이터 없음")
  PROMPT_MAX_TRIAL_FAILED = (HTTPStatus.INTERNAL_SERVER_ERROR, "S004", "프롬프트 응답 재요청 3회 시도 진행 결과 json 불일치")
  COLLECTION_NOT_FOUND = (HTTPStatus.BAD_REQUEST, "S005", "요청 카테고리에 해당하는 컬렉션 없음")
  STANDARD_REVIEW_FAIL = (HTTPStatus.INTERNAL_SERVER_ERROR, "S006", "기준문서 AI 데이터 생성 작업 중 에러 발생")
  BUILD_POINT_FAILED = (HTTPStatus.INTERNAL_SERVER_ERROR, "S007", "포인트 생성 과정 내 에러 발견")

  # common 에러

  FILE_LOAD_FAILED = (HTTPStatus.BAD_REQUEST, "C002", "S3에서 파일을 가져 오지 못함")
  S3_CLIENT_ERROR = (HTTPStatus.INTERNAL_SERVER_ERROR, "C003", "S3 연결 도중 에러 발생")
  INVALID_FILE_STREAM = (HTTPStatus.INTERNAL_SERVER_ERROR, "C004", "유효하지 않은 파일 url")

  FILE_FORMAT_INVALID = (HTTPStatus.INTERNAL_SERVER_ERROR, "C006", "파일이 깨졌거나 지원 불가")
  S3_STREAM_READ_FAILED = (HTTPStatus.INTERNAL_SERVER_ERROR, "C007", "S3 스트림을 읽는 중 에러 발생")
  INVALID_JSON_FORMAT = (HTTPStatus.BAD_REQUEST, "C008", "입력 형태가 JSON 형식에 맞지 않음")
  FIELD_MISSING = (HTTPStatus.BAD_REQUEST, "C009", "JSON에 필수 필드가 누락됨")
  INVALID_URL_PARAMETER = (HTTPStatus.BAD_REQUEST, "C010", "url 경로에 필수 항목이 누락됨")
  CANNOT_CONVERT_TO_NUM = (HTTPStatus.BAD_REQUEST, "C011", "URL 매개변수를 숫자로 변환할 수 없음")
  EMBEDDING_FAILED = (HTTPStatus.INTERNAL_SERVER_ERROR, "C012", "임베딩 실패")
  NO_POINTS_GENERATED = (HTTPStatus.INTERNAL_SERVER_ERROR, "C013", "생성된 포인트 없음")
  QDRANT_CONNECTION_TIMEOUT = (HTTPStatus.INTERNAL_SERVER_ERROR, "C014", "Qdrant 연결 타임 아웃")
  QDRANT_NOT_STARTED = (HTTPStatus.NOT_FOUND, "C015", "Qdrant 실행 여부 확인 필요")
  NO_TEXTS_EXTRACTED = (HTTPStatus.INTERNAL_SERVER_ERROR, "C016", "해당 파일에서 추출된 텍스트 없음")
  PDF_LOAD_FAILED = (HTTPStatus.INTERNAL_SERVER_ERROR, "C017", "PDF 로딩 실패")
  LLM_RESPONSE_TIMEOUT = (HTTPStatus.INTERNAL_SERVER_ERROR, "C018", "LLM 응답 시간 초과")

  # agreement 관련 에러



  QDRANT_SEARCH_FAILED = (HTTPStatus.INTERNAL_SERVER_ERROR, "A004", "Qdrant 검색 결과 반환 실패")
  NO_POINTS_FOUND = (HTTPStatus.INTERNAL_SERVER_ERROR, "A005", "Qdrant 내 조회 가능한 포인트 없음")
  CHUNK_ANALYSIS_FAILED = (HTTPStatus.INTERNAL_SERVER_ERROR, "A006", "계약서 분석 내 누락건으로 인해 분석 실패")
  NO_SEPARATOR_FOUND = (HTTPStatus.INTERNAL_SERVER_ERROR, "A007", "원문 분리 인자 발견 못함")
  UNSUPPORTED_FILE_TYPE = (HTTPStatus.BAD_REQUEST, "A008", "지원되지 않는 타입의 파일")

  NAVER_OCR_REQUEST_FAIL = (HTTPStatus.INTERNAL_SERVER_ERROR, "A010", "네이버 OCR 요청 실패")
  NAVER_OCR_SETTING_LOAD_FAIL = (HTTPStatus.INTERNAL_SERVER_ERROR, "A011", "API_URL 또는 API_KEY 환경변수가 설정되지 않음")

  def __init__(self, status: HTTPStatus, code: str, message: str):
    self.status = status
    self.code = code
    self.message = message
