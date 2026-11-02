import threading
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from techtest.models import ScalarResults
from techtest.risk_system import ParallelPricer, SerialPricer


def trade(trade_id, trade_type='test'):
    return SimpleNamespace(trade_id=trade_id, trade_type=trade_type)


class ParallelPricerTests(unittest.TestCase):
    def test_parallel_work_waits_and_limits_feed_consumption(self):
        started = threading.Barrier(3)
        release = threading.Event()
        loaded = []
        results = ScalarResults()
        errors = []

        class Engine:
            def price(self, item, receiver):
                started.wait(timeout=5)
                if not release.wait(timeout=5):
                    raise TimeoutError('workers were not released')
                receiver.add_result(item.trade_id, 10.0)

        def load_pricers(pricer):
            pricer._pricers['test'] = Engine()

        def feed():
            for i in range(3):
                loaded.append(i)
                yield trade(str(i), 'test' if i < 2 else 'unknown')

        def run():
            try:
                ParallelPricer(max_workers=2).price([feed()], results)
            except Exception as exc:
                errors.append(exc)

        with patch.object(SerialPricer, '_load_pricers', load_pricers):
            thread = threading.Thread(target=run)
            thread.start()
            try:
                started.wait(timeout=5)
                self.assertEqual(loaded, [0, 1])
                self.assertTrue(thread.is_alive())
            finally:
                release.set()
                thread.join(timeout=5)
        self.assertFalse(thread.is_alive())
        self.assertEqual(errors, [])
        self.assertEqual(results['0'].result, 10.0)
        self.assertEqual(results['1'].result, 10.0)
        self.assertEqual(results['2'].error, 'No Pricing Engines available for this trade type')

    def test_result_and_warning_are_both_forwarded(self):
        class Engine:
            def price(self, item, receiver):
                receiver.add_result(item.trade_id, 12.0)
                receiver.add_error(item.trade_id, 'warning')

        def load_pricers(pricer):
            pricer._pricers['test'] = Engine()

        results = ScalarResults()
        with patch.object(SerialPricer, '_load_pricers', load_pricers):
            ParallelPricer().price([[trade('one')]], results)
        self.assertEqual(results['one'].result, 12.0)
        self.assertEqual(results['one'].error, 'warning')

    def test_worker_exception_is_raised(self):
        class Engine:
            def price(self, item, receiver):
                raise RuntimeError('pricing failed')

        def load_pricers(pricer):
            pricer._pricers['test'] = Engine()

        with patch.object(SerialPricer, '_load_pricers', load_pricers):
            with self.assertRaisesRegex(RuntimeError, 'pricing failed'):
                ParallelPricer().price([[trade('one')]], ScalarResults())

    def test_empty_input_and_invalid_worker_count(self):
        results = ScalarResults()
        ParallelPricer().price([], results)
        self.assertEqual(list(results), [])
        with self.assertRaises(ValueError):
            ParallelPricer(max_workers=0)


if __name__ == '__main__':
    unittest.main()
