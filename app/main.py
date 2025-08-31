import asyncio
import datetime as dt

import ccxt.pro as ccxtpro
import pandas as pd
from coin_handlers import main_pattern_handler
from loguru import logger
from scheduler.asyncio import Scheduler
from trading import Controller

logger.add("log.txt", rotation="10MB")


async def sort_symbols(exchange, symbols: list[str]):
    vals = await asyncio.gather(
        *[exchange.fetch_ohlcv(sym, "1d", limit=1) for sym in symbols]
    )

    return sorted(symbols, key=lambda x: vals[symbols.index(x)][0][-1], reverse=True)


async def main():
    exchange = ccxtpro.bybit()
    markets = await exchange.load_markets()
    df = pd.DataFrame(markets).T.reset_index(drop=True)
    symbols = df[(df["type"] == "swap") & df["active"]]["symbol"].tolist()
    symbols = (await sort_symbols(exchange, symbols))[:300]

    logger.info(f"finding {len(symbols)} symbols")

    controller = Controller(symbols, exchange)
    logger.info("Initing...")
    await controller.init()
    logger.info("Controller inited")
    for symbol in controller.symbols:
        symbol.last_alert = 1

    # with open("./app/screener.json") as f:
    #     screener_settings = json.load(f)

    controller.add_handler(main_pattern_handler)
    # for handler in screener_settings:
    # logger.info(f"New handler: {handler}")
    # if handler["type"] == "price":
    #     controller.add_handler(
    #         price_up_down_handler(handler["value"], handler["timeframe"])
    #     )

    scheduler = Scheduler()
    scheduler.minutely(dt.time(second=5), controller.update)
    logger.info("Bot runned")
    while True:
        await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
