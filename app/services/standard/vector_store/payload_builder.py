from datetime import datetime
from zoneinfo import ZoneInfo

from app.containers.service_container import prompt_service
from app.models.vector import VectorPayload
from app.services.common.llm_retry import retry_llm_call

STANDARD_LLM_REQUIRED_KEYS = {"incorrect_text", "corrected_text"}


async def make_clause_payload(prompt_client, article, pdf_request,
    semaphore) -> VectorPayload | None:
  async with semaphore:
    result = await retry_llm_call(
        prompt_service.make_correction_data,
        prompt_client, article,
        required_keys=STANDARD_LLM_REQUIRED_KEYS
    )
    if not result:
      return None

  korea_time = datetime.now(ZoneInfo("Asia/Seoul"))
  return VectorPayload(
      standard_id=pdf_request.id,
      incorrect_text=result.get("incorrect_text") or "",
      proof_text=article.clause_content,
      corrected_text=result.get("corrected_text") or "",
      created_at=korea_time.strftime("%Y-%m-%d %H:%M:%S")
  )
