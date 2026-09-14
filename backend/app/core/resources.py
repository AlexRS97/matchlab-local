"""Apply the desktop resource budget before importing numerical libraries."""

import os
import sys


def configure_resources():
    for name in (
        "OMP_NUM_THREADS",
        "OPENBLAS_NUM_THREADS",
        "MKL_NUM_THREADS",
        "NUMEXPR_NUM_THREADS",
    ):
        os.environ[name] = "2"
    # Local training and inference always use CPU; leave the graphics card available.
    os.environ["CUDA_VISIBLE_DEVICES"] = ""
    if sys.platform == "win32":
        import ctypes

        kernel = ctypes.windll.kernel32
        kernel.GetCurrentProcess.restype = ctypes.c_void_p
        kernel.SetPriorityClass.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
        kernel.SetPriorityClass(
            kernel.GetCurrentProcess(), 0x00004000
        )  # BELOW_NORMAL_PRIORITY_CLASS
