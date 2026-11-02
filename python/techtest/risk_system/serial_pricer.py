from __future__ import annotations

import importlib
import os
from typing import Iterable

from techtest.models import PricingEngine, ResultReceiver, Trade
from techtest.risk_system.pricing_config_loader import PricingConfigLoader


class SerialPricer:
    def __init__(self) -> None:
        self._pricers: dict[str, PricingEngine] = {}

    def price(self, trade_containers: Iterable[Iterable[Trade]], result_receiver: ResultReceiver) -> None:
        self._load_pricers()

        for trade_container in trade_containers:
            for trade in trade_container:
                self.price_trade(trade, result_receiver)

    def price_trade(self, trade: Trade, result_receiver: ResultReceiver) -> None:
        """Price one trade using the engines already loaded for this pricer."""
        pricer = self._pricers.get(trade.trade_type)
        if pricer is None:
            result_receiver.add_error(trade.trade_id, "No Pricing Engines available for this trade type")
            return
        pricer.price(trade, result_receiver)

    def _load_pricers(self) -> None:
        pricing_config_loader = PricingConfigLoader()
        pricing_config_loader.config_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "pricing_config", "PricingEngines.xml")
        pricer_config = pricing_config_loader.load_config()

        for config_item in pricer_config:
            module = importlib.import_module(config_item.module)
            engine_class = getattr(module, config_item.class_name)
            self._pricers[config_item.trade_type] = engine_class()
