from dataclasses import dataclass
from flask import jsonify


@dataclass
class ErrorResponse:
  code: str
  message: str

  @staticmethod
  def of(code: str, message: str):
    response = {
      "code": code,
      "message": message
    }
    return jsonify(response)

