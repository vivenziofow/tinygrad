from tinygrad.helpers import Timing
from typing import Any
import cloudpickle
import subprocess
import multiprocessing

def _early_exec_process(qin, qout):
  while True:
    path, inp = qin.get()
    try:
      qout.put(subprocess.check_output(path, input=inp))
    except subprocess.CalledProcessError as e:
      qout.put(e)

def enable_early_exec():
  qin: multiprocessing.Queue = multiprocessing.Queue()
  qout: multiprocessing.Queue = multiprocessing.Queue()
  p = multiprocessing.Process(target=_early_exec_process, args=(qin, qout))
  p.daemon = True
  p.start()
  def early_exec(x):
    qin.put(x)
    ret = qout.get()
    if isinstance(ret, Exception): raise ret
    else: return ret
  return early_exec

def proc(itermaker, q) -> None:
  for x in itermaker(): q.put(x)
  q.put(None)
  q.close()

class _CloudpickleFunctionWrapper:
  def __init__(self, fn):
    self.fn = fn

  def __getstate__(self):
    return cloudpickle.dumps(self.fn)

  def __setstate__(self, pfn):
    self.fn = cloudpickle.loads(pfn)

  def __call__(self, *args, **kwargs) -> Any:
    return self.fn(*args, **kwargs)

def cross_process(itermaker, maxsize=16):
  q: multiprocessing.Queue = multiprocessing.Queue(maxsize)
  # multiprocessing uses pickle which cannot dump lambdas, so use cloudpickle.
  p = multiprocessing.Process(target=proc, args=(_CloudpickleFunctionWrapper(itermaker), q))
  #p.daemon = True
  p.start()

  # TODO: write tests and handle exit case
  while True:
    ret = q.get()
    if ret is None: break
    yield ret
