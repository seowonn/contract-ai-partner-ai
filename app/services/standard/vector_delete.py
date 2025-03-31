from httpx import ConnectTimeout
from qdrant_client.http.exceptions import UnexpectedResponse, \
  ResponseHandlingException
from qdrant_client.models import Filter, FieldCondition, MatchValue

from app.blueprints.standard.standard_exception import StandardException
from app.clients.qdrant_client import get_qdrant_client
from app.common.exception.custom_exception import BaseCustomException
from app.common.exception.error_code import ErrorCode
from app.schemas.success_code import SuccessCode


async def delete_by_standard_id(standard_id: int, collection_name: str) -> SuccessCode:
  filter_condition = Filter(
      must=[
        FieldCondition(key="standard_id", match=MatchValue(value=standard_id))]
  )

  client = get_qdrant_client()
  try:
    points, _ = await client.scroll(
      collection_name=collection_name,
      scroll_filter=filter_condition,
      limit=1
    )
  except (ConnectTimeout, ResponseHandlingException):
    raise BaseCustomException(ErrorCode.QDRANT_CONNECTION_TIMEOUT)
  finally:
    await client.aclose()

  if not points:
    return SuccessCode.NO_DOCUMENT_FOUND

  try:
    await client.delete(
      collection_name=collection_name,
      points_selector=filter_condition
    )
  except UnexpectedResponse:
    raise StandardException(ErrorCode.DELETE_FAIL)

  except (ConnectTimeout, ResponseHandlingException):
    raise BaseCustomException(ErrorCode.QDRANT_CONNECTION_TIMEOUT)
  finally:
    await client.aclose()

  return SuccessCode.DELETE_SUCCESS