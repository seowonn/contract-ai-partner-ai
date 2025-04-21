import logging
import time
from functools import wraps

from flask import request
from pydantic import ValidationError

from app.common.exception.custom_exception import CommonException
from app.common.exception.error_code import ErrorCode


def parse_request(model_cls):
  def decorator(func):
    @wraps(func)
    def wrapper(*args, **kwargs):

      try:
        json_data = request.get_json()
        if json_data is None:
          raise CommonException(ErrorCode.INVALID_JSON_FORMAT)
        model_instance = model_cls(**json_data)
        return func(model_instance, *args, **kwargs)

      except ValidationError:
        raise CommonException(ErrorCode.FIELD_MISSING)

    return wrapper

  return decorator


def measure_time(func):
  @wraps(func)
  def wrapper(*args, **kwargs):
    start_time = time.time()
    result = func(*args, **kwargs)
    logging.info(f"[{func.__name__}] 소요시간: {time.time() - start_time:.4f}초")
    return result

  return wrapper


def async_measure_time(func):
  @wraps(func)
  async def wrapper(*args, **kwargs):
    start_time = time.time()
    result = await func(*args, **kwargs)
    logging.info(f"[{func.__name__}] 실행 시간: {time.time() - start_time:.4f}초")
    return result

  return wrapper