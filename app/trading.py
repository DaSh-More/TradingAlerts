import asyncio
from types import CoroutineType

from ccxt.base.exchange import Exchange
from loguru import logger


class Symbol:
    def __init__(self, symbol: str, exchange: Exchange):
        self.symbol = symbol
        self.exchange = exchange
        self.candles = []
        self.candles_limit = 500

    async def get_old_candles(self):
        try:
            self.candles = await self.exchange.fetch_ohlcv(
                self.symbol, "1m", limit=self.candles_limit
            )
        except Exception as e:
            logger.error(e)

    async def update(self):
        try:
            candle = (await self.exchange.watch_ohlcv(self.symbol, "1m"))[0]
            if self.candles[-1] != candle:
                self.candles.append(candle)
                self.candles.pop(0)
                return True
        except Exception as e:
            logger.error(e)

    def __repr__(self):
        return f"<Symbol [{self.symbol}]>"


class Controller:
    def __init__(self, symbols: list[str], exchange: Exchange):
        self.exchange = exchange
        self.symbols: list[Symbol] = [Symbol(s, exchange) for s in symbols]
        self.__handlers = []

    async def init(self):
        tasks = [sym.get_old_candles() for sym in self.symbols]
        await asyncio.gather(*tasks)

    async def update(self):
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
