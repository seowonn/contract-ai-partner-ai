from qdrant_client.http.exceptions import UnexpectedResponse
from qdrant_client.models import Filter, FieldCondition, MatchValue

from app.blueprints.standard.standard_exception import StandardException
from app.clients.qdrant_client import get_qdrant_client
from app.common.constants import Constants
from app.common.exception.error_code import ErrorCode
from app.schemas.success_code import SuccessCode


async def delete_by_standard_id(standard_id: int) -> SuccessCode:
  filter_condition = Filter(
      must=[
        FieldCondition(key="standard_id", match=MatchValue(value=standard_id))]
  )

  points, _ = await get_qdrant_client.scroll(
      collection_name=Constants.QDRANT_COLLECTION.value,
      scroll_filter=filter_condition,
      limit=1
  )

  if not points:
    return SuccessCode.NO_DOCUMENT_FOUND

  try:
    await get_qdrant_client.delete(
        collection_name=Constants.QDRANT_COLLECTION.value,
        points_selector=filter_condition
    )
  except UnexpectedResponse:
    raise StandardException(ErrorCode.DELETE_FAIL)

  return SuccessCode.DELETE_SUCCESS
