import asyncio
import json
from types import CoroutineType

from ccxt.base.exchange import Exchange
from loguru import logger


class Symbol:
    def __init__(self, symbol: str, exchange: Exchange):
        self.symbol = symbol
        self.exchange = exchange
        self.candles = []
        self.open_interest = []
        self.candles_limit = 60

    async def get_history_data(self):
        try:
            # Получаем исторические свечи
            self.candles = await self.exchange.fetch_ohlcv(
                self.symbol, "1m", limit=self.candles_limit
            )
            await self.__get_oi()

        except Exception as e:
            logger.error(f"{self.symbol}: {e}")

    async def __get_oi(self):
        data = await self.exchange.fetch_open_interest_history(
            self.symbol, "5m", limit=self.candles_limit // 5
        )
        self.open_interest = [oi["openInterestValue"] for oi in (data)]

    async def update(self):
        try:
            # Обновляем свечи
            candle = (await self.exchange.fetch_ohlcv(self.symbol, "1m"))[0]
            if self.candles[-1] != candle:
                self.candles.append(candle)
                self.candles.pop(0)

            # Пытаемся обновить открытый интерес
            await self.__get_oi()
            self.dump()

            return True
        except Exception as e:
            logger.error(e)

    def dump(self):
        with open(f"./app/logs/{self.symbol.split('/')[0]}.json", "w") as f:
            json.dump({"oi": self.open_interest, "candles": self.candles}, f)

    def __repr__(self):
        return f"<Symbol [{self.symbol}]>"


class Controller:
    def __init__(self, symbols: list[str], exchange: Exchange):
        self.exchange = exchange
        self.symbols: list[Symbol] = [Symbol(s, exchange) for s in symbols]
        self.__handlers = []

    async def init(self):
        tasks = [sym.get_history_data() for sym in self.symbols]
        await asyncio.gather(*tasks)

    async def update(self):
        logger.info("updated")
        updates = await asyncio.gather(*[sym.update() for sym in self.symbols])
        if not any(updates):
            logger.warning("no updates")
            return
        tasks = []
        for handler in self.__handlers:
            logger.info(f"Check handler '{handler['title']}'")
            for symbol in self.symbols:
                res = handler["func"](symbol)
                if isinstance(res, CoroutineType):
                    tasks.append(res)
        await asyncio.gather(*tasks)

    def add_handler(self, handler):
        self.__handlers.append({"title": hash(handler), "func": handler})
