import os
import tempfile
import unittest
from unittest.mock import patch

from techtest.loaders import TRADE_DATA_DIR, BondTradeLoader, FxTradeLoader
from techtest.models import ScalarResults
from techtest.risk_system import SerialPricer, SerialTradeLoader


class TradeStreamingTests(unittest.TestCase):
    def test_loaders_parse_only_as_trades_are_requested(self):
        for loader_type, filename, headers in (
            (BondTradeLoader, 'BondTrades.dat', 1),
            (FxTradeLoader, 'FxTrades.dat', 2),
        ):
            with self.subTest(loader=loader_type.__name__):
                with open(os.path.join(TRADE_DATA_DIR, filename), encoding='utf-8-sig') as source:
                    lines = [next(source) for _ in range(headers + 1)]
                with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', delete=False) as feed:
                    feed.writelines(lines)
                    feed.write('malformed\n')
                    path = feed.name
                self.addCleanup(os.unlink, path)
                trades = iter(loader_type(path).load_trades())
                self.assertIsNotNone(next(trades))
                with self.assertRaises((IndexError, ValueError)):
                    next(trades)

    def test_pricing_occurs_before_next_trade_is_loaded(self):
        events = []

        class Trade:
            trade_type = 'test'
            trade_id = 'first'

        class Engine:
            def price(self, trade, receiver):
                events.append('price')

        def trades():
            events.append('load first')
            yield Trade()
            events.append('load second')

        pricer = SerialPricer()
        pricer._pricers['test'] = Engine()
        with patch.object(pricer, '_load_pricers'):
            pricer.price([trades()], ScalarResults())
        self.assertEqual(events, ['load first', 'price', 'load second'])

    def test_sources_are_requested_one_at_a_time(self):
        events = []

        class Loader:
            def __init__(self, name):
                self.name = name

            def load_trades(self):
                events.append(self.name)
                return iter(())

        loader = SerialTradeLoader()
        with patch.object(loader, '_get_trade_loaders', return_value=[Loader('first'), Loader('second')]):
            sources = iter(loader.load_trades())
            next(sources)
            self.assertEqual(events, ['first'])
            next(sources)
            self.assertEqual(events, ['first', 'second'])


if __name__ == '__main__':
    unittest.main()
