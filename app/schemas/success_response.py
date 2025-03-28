from dataclasses import asdict, is_dataclass, dataclass
from typing import Optional, Any

from flask import jsonify

from app.schemas.success_code import SuccessCode


@dataclass
class SuccessResponse:
  success: SuccessCode
  data: Optional[Any] = None

  def of(self):
    response_data = self._convert_data(self.data)

    return jsonify({
      "code": self.success.code,
      "message": self.success.message,
      "data": response_data if self.data else None
    })

  def _convert_data(self, data: Any) -> Any:
    if is_dataclass(data):
      return self.convert_keys_to_camel_case(asdict(data))
    elif isinstance(data, list):
      return [
        self._convert_data(item) for item in data
      ]
    elif isinstance(data, dict):
      return self.convert_keys_to_camel_case(data)
    else:
      return data

  @staticmethod
  def convert_keys_to_camel_case(data: Any) -> Any:
    if isinstance(data, dict):
      return {SuccessResponse.to_camel_case(
        k): SuccessResponse.convert_keys_to_camel_case(v) for k, v in
              data.items()}
    elif isinstance(data, list):
      return [SuccessResponse.convert_keys_to_camel_case(item) for item in data]
    else:
      return data

  @staticmethod
  def to_camel_case(snake_str: str) -> str:
    parts = snake_str.split('_')
    return parts[0] + ''.join(word.capitalize() for word in parts[1:])
