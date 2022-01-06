from decimal import Decimal
from typing import (
    Set,
    Tuple,
    List
)
import psutil
import datetime
import asyncio


s_decimal_0 = Decimal("0")


def format_bytes(size):
    for unit in ["B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB"]:
        if abs(size) < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} YB"


async def start_timer(timer):
    count = 1
    while True:
        count += 1
        timer.log(f"Duration: {datetime.timedelta(seconds=count)}")
        await _sleep(1)


async def _sleep(delay):
    """
    A wrapper function that facilitates patching the sleep in unit tests without affecting the asyncio module
    """
    await asyncio.sleep(delay)


async def start_process_monitor(process_monitor):
    hb_process = psutil.Process()
    while True:
        with hb_process.oneshot():
            threads = hb_process.num_threads()
            process_monitor.log("CPU: {:>5}%, ".format(hb_process.cpu_percent()) +
                                "Mem: {:>10} ({}), ".format(
                                    format_bytes(hb_process.memory_info().vms / threads),
                                    format_bytes(hb_process.memory_info().rss)) +
                                "Threads: {:>3}, ".format(threads)
                                )
        await _sleep(1)

