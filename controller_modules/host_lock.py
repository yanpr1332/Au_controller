"""Cross-process serialization of Audition requests, independent of CEP."""
from contextlib import contextmanager
import msvcrt
import time


@contextmanager
def audition_host_lock(directory, timeout):
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / 'audition_host.lock'
    with path.open('a+b') as handle:
        handle.seek(0, 2)
        if handle.tell() == 0:
            handle.write(b'0'); handle.flush()
        deadline = time.monotonic() + timeout
        while True:
            handle.seek(0)
            try:
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                break
            except OSError:
                if time.monotonic() >= deadline:
                    raise TimeoutError('Audition host is occupied by another controller request')
                time.sleep(.05)
        try:
            yield
        finally:
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
