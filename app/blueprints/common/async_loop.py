import asyncio


def run_async(core):
  loop = asyncio.new_event_loop()
  asyncio.set_event_loop(loop)
  try:
    return loop.run_until_complete(core)
  finally:
    loop.close()