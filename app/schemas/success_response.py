from dataclasses import dataclass, asdict, is_dataclass
from typing import Optional, Any

from flask import jsonify

from app.schemas.success_code import SuccessCode


@dataclass
class SuccessResponse:
  success: SuccessCode
  data: Optional[Any] = None

  def of(self):
    # 인스턴스(속성 정보가 들어간게)가 아니라 클래스 자체(껍데기)일 수도 있어 검사가 필요함
    if is_dataclass(self.data) and not isinstance(self.data, type):
      response_data = self.convert_keys_to_camel_case(asdict(self.data))
    else:
      response_data = self.convert_keys_to_camel_case(self.data)

    return jsonify({
      "code": self.success.code,
      "message": self.success.message,
      "data": response_data if self.data else None
    })

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
