from __future__ import annotations

import xml.etree.ElementTree as ET

from techtest.risk_system.pricing_engine_config import PricingEngineConfig
from techtest.risk_system.pricing_engine_config_item import PricingEngineConfigItem


class PricingConfigLoader:
    def __init__(self) -> None:
        self.config_file: str | None = None

    def load_config(self) -> PricingEngineConfig:
        root = ET.parse(self.config_file).getroot()
        config = PricingEngineConfig()

        for engine in root.findall("Engine"):
            config.append(
                PricingEngineConfigItem(
                    trade_type=engine.attrib["tradeType"],
                    module=engine.attrib["module"],
                    class_name=engine.attrib["class"],
                )
            )

        return config
