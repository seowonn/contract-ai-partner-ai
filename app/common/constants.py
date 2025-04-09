SUCCESS = "success"

ARTICLE_HEADER_PATTERN = r'^\s*제\s*\d+\s*조'
ARTICLE_CHUNK_PATTERN = r'(제\d+조\s*(?:【[^】]+】|\([^)]+\)))(.*?)(?=(?:제\d+조\s*(?:【[^】]+】|\([^)]+\))|$))'
ARTICLE_HEADER_PARSE_PATTERN = r'제(\d+)조\s*(?:【([^】]+)】|\(([^)]+)\))'

CLAUSE_HEADER_PATTERN = r'(①|1\.|\(1\))'

CLAUSE_TEXT_SEPARATOR = "!!!"
ARTICLE_CLAUSE_SEPARATOR = "+"

MAX_RETRIES = 5

