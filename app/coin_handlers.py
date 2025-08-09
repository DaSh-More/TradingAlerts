import asyncio

from bot import send_signal
from jinja2 import Environment, FileSystemLoader
from loguru import logger
from trading import Symbol

env = Environment(loader=FileSystemLoader("./app/templates"))


def long_short_handler(percent: float, timeframe: int):
    async def func(symbol: Symbol):
        candles = symbol.candles[-timeframe:]
        # Ищем максимальный рост за последние {timeframe} минут
        # o, h, l, c, v = zip(*candles)

        max_price = candles[0][1]  # начальный максимум
        min_price = candles[0][2]  # начальный минимум

        max_growth = 0
        max_fall = 0

        for candle in candles:
            current_high = candle[1]
            current_low = candle[2]

            # Обновляем максимальный рост, если current_high - min_price > рекорда
            potential_growth = current_high - min_price
            max_growth = max(max_growth, potential_growth)

            potential_fall = max_price - current_low
            max_fall = max(max_fall, potential_fall)

            # Обновляем минимум, если нашли новый
            max_price = max(current_high, max_price)
            min_price = min(current_low, min_price)

        grow_p = max_growth / min_price
        fall_p = -(max_fall / max_price)
        change = grow_p if percent > 0 else fall_p

        logger.info(f"{symbol.symbol} change {change}")
        if abs(change) >= abs(percent):
            if symbol.last_alert > 0:
                symname = symbol.symbol.split(":")[0]
                template = env.get_template("long_short_signal.jinja2")
                await send_signal(template.render(symname=symname, change=change))

            symbol.last_alert = 0
        else:
            symbol.last_alert += 1
    return func
