from __future__ import annotations

from collections import deque
from concurrent.futures import ThreadPoolExecutor
from threading import local
from typing import Iterable

from techtest.models import ResultReceiver, Trade
from techtest.risk_system.serial_pricer import SerialPricer


class _CollectedResults(ResultReceiver):
    """Record receiver calls so only the calling thread touches the real receiver."""

    def __init__(self) -> None:
        self.calls = []

    def add_result(self, trade_id: str, result: float) -> None:
        self.calls.append(("add_result", trade_id, result))

    def add_error(self, trade_id: str, error: str | None) -> None:
        self.calls.append(("add_error", trade_id, error))


class ParallelPricer:
    def __init__(self, max_workers: int = 4) -> None:
        if max_workers < 1:
            raise ValueError("max_workers must be at least 1")
        self._max_workers = max_workers

    def price(self, trade_containers: Iterable[Iterable[Trade]], result_receiver: ResultReceiver) -> None:
        workers = local()

        def price_trade(trade: Trade) -> _CollectedResults:
            if not hasattr(workers, "pricer"):
                workers.pricer = SerialPricer()
                workers.pricer._load_pricers()
            results = _CollectedResults()
            workers.pricer.price_trade(trade, results)
            return results

        def collect(future) -> None:
            for method, trade_id, value in future.result().calls:
                getattr(result_receiver, method)(trade_id, value)

        with ThreadPoolExecutor(max_workers=self._max_workers) as executor:
            pending = deque()
            for container in trade_containers:
                for trade in container:
                    pending.append(executor.submit(price_trade, trade))
                    if len(pending) >= self._max_workers:
                        collect(pending.popleft())
            while pending:
                collect(pending.popleft())
