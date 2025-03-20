from qdrant_client.http.exceptions import UnexpectedResponse
from qdrant_client.models import Filter, FieldCondition, MatchValue

from app.blueprints.standard.standard_exception import StandardException
from app.clients.qdrant_client import qdrant_db_client
from app.common.exception.error_code import ErrorCode
from app.schemas.success_code import SuccessCode


def delete_by_standard_id(standard_id: int) -> SuccessCode:
  filter_condition = Filter(
      must=[
        FieldCondition(key="standard_id", match=MatchValue(value=standard_id))]
  )

  points, _ = qdrant_db_client.scroll(
      collection_name="standard",
      scroll_filter=filter_condition,
      limit=1
  )

  if not points:
    return SuccessCode.NO_DOCUMENT_FOUND

  try:
    qdrant_db_client.delete(
        collection_name="standard",
        points_selector=filter_condition
    )
  except UnexpectedResponse:
    raise StandardException(ErrorCode.DELETE_FAIL)

  return SuccessCode.DELETE_SUCCESS
