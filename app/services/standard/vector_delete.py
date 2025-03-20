from qdrant_client.http.exceptions import UnexpectedResponse

from app.blueprints.standard.standard_exception import StandardException
from app.clients.qdrant_client import qdrant_db_client
from qdrant_client import models

from app.common.exception.error_code import ErrorCode


def delete_by_standard_id(standard_id: int):
  filter_condition = models.Filter(
      must=[models.FieldCondition(key="standard_id",
                                  match=models.MatchValue(value=standard_id))]
  )

  existing_data = qdrant_db_client.scroll(collection_name="standard",
                                          scroll_filter=filter_condition,
                                          limit=1)

  if len(existing_data[0]) == 0:
    raise StandardException(ErrorCode.NOT_FOUND)
  try:
    qdrant_db_client.delete(
        collection_name="standard",
        points_selector=filter_condition
    )
  except UnexpectedResponse:
    raise StandardException(ErrorCode.DELETE_FAIL)

  return 200
