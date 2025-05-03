SUCCESS = "success"

ARTICLE_HEADER_PATTERN = r'^\s*제\s*\d+\s*조'
ARTICLE_CHUNK_PATTERN = r'(제\s*\d+\s*조\s*(?:【[^】\n]*】?|[^】\n]*】|\([^)\\n]*\)?|\[[^\]\n]*\]?))\s*(.*?)(?=(?:제\s*\d+\s*조\s*(?:【[^】\n]*】?|[^】\n]*】|\([^)\\n]*\)?|\[[^\]\n]*\]?|)|$))'


ARTICLE_HEADER_PARSE_PATTERN = r'제\s*(\d+)\s*조\s*(?:【([^】]+)】|\(([^)]+)\)|\[([^\]]+)\])'
NUMBER_HEADER_PATTERN = r'(\d+\.\s*[^\n:：]+)\s*[:：]?\s*(.*?)(?=\d+\.\s|$)'

CLAUSE_HEADER_PATTERN = r'(①|1\.|\(1\))'

CLAUSE_TEXT_SEPARATOR = "!!!"
ARTICLE_CLAUSE_SEPARATOR = "+"

MAX_RETRIES = 5
LLM_TIMEOUT = 30.0

PROMPT_MODEL = "gpt-4.1-mini"
EMBEDDING_MODEL = "text-embedding-3-small"