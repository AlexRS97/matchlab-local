"""Use the available CPU capacity while the manually launched application is running."""

import os
import sys


def available_cpu_threads() -> int:
    affinity = getattr(os, "sched_getaffinity", None)
    if affinity:
        try:
            return max(1, len(affinity(0)))
        except OSError:
            pass
    return max(1, os.cpu_count() or 1)


def resolve_threads(value: int | str | None = None) -> int:
    available = available_cpu_threads()
    if value is None or value == "auto":
        return available
    requested = int(value)
    if requested < 1:
        raise ValueError("El número de hilos debe ser positivo o auto")
    return min(requested, available)


def configure_resources():
    threads = str(available_cpu_threads())
    for name in (
        "OMP_NUM_THREADS",
        "OPENBLAS_NUM_THREADS",
        "MKL_NUM_THREADS",
        "NUMEXPR_NUM_THREADS",
    ):
        os.environ[name] = threads
    if sys.platform == "win32":
        import ctypes

        kernel = ctypes.windll.kernel32
        kernel.GetCurrentProcess.restype = ctypes.c_void_p
        kernel.SetPriorityClass.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
        kernel.SetPriorityClass(kernel.GetCurrentProcess(), 0x00000020)  # NORMAL_PRIORITY_CLASS
