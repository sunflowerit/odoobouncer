import asyncio
from concurrent.futures import ThreadPoolExecutor

def force_async(func):
  # Convert a sync function into an asycn function using threads
  
  # Note: this does not work with all functions in the RequestHandler class (i.e. functions using self.render)
  # Make the functions in the requesthandler async and use this decorator on the functions slowing the requesthandler down

  pool=ThreadPoolExecutor()
  def wrapper(*args,**kwargs):
    future=pool.submit(func,*args,**kwargs)
    return asyncio.wrap_future(future)
  return wrapper
