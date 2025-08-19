import asyncio
from math import ceil

from jinja2 import Environment, FileSystemLoader
from loguru import logger

from .bot import send_signal
from .trading import Symbol

env = Environment(loader=FileSystemLoader("./app/templates"))


def get_change_price(symbol: Symbol, timeframe: int):
    candles = symbol.candles[-timeframe:]
    # Ищем максимальный рост за последние {timeframe} минут
    # o, h, l, c, v = zip(*candles)

    max_price = candles[0][2]  # начальный максимум
    min_price = candles[0][3]  # начальный минимум

    max_growth = 0
    max_fall = 0

    for candle in candles:
        current_high = candle[2]
        current_low = candle[3]

        # Обновляем максимальный рост, если current_high - min_price > рекорда
        potential_growth = current_high - min_price
        max_growth = max(max_growth, potential_growth)

        potential_fall = max_price - current_low
        max_fall = max(max_fall, potential_fall)

        # Обновляем минимум, если нашли новый
        max_price = max(current_high, max_price)
        min_price = min(current_low, min_price)

    grow_p = max_growth / min_price
    fall_p = max_fall / max_price
    return grow_p, fall_p


def price_up_down_handler(percent: float, timeframe: int):
    async def func(symbol: Symbol):
        # Ищем максимальный рост за последние {timeframe} минут
        # o, h, l, c, v = zip(*candles)
        grow_p, fall_p = get_change_price(symbol, timeframe)
        change = grow_p if percent > 0 else fall_p

        logger.info(f"{symbol.symbol} change {change}")
        if change >= abs(percent):
            if symbol.last_alert > 0:
                symname = symbol.symbol.split(":")[0]
                template = env.get_template("price_signal.jinja2")
                await send_signal(template.render(symname=symname, change=change))

            symbol.last_alert = 0
        else:
            symbol.last_alert += 1

    return func


def get_oi_change(symbol: Symbol, timeframe: int):
    if not symbol.open_interest:
        logger.warning(f"Symbol [{symbol.symbol}] don't has OI!")
        return 0, 0
    
    ois = symbol.open_interest[-ceil(timeframe / 5) :]
    # Ищем максимальный рост за последние {timeframe} минут

    min_oi = max_oi = ois[0]  # начальный минимум и максимум

    max_growth = 0
    max_fall = 0

    for value in ois:
        # Обновляем максимальный рост, если current_high - min_price > рекорда
        potential_growth = value - min_oi
        max_growth = max(max_growth, potential_growth)

        potential_fall = max_oi - value
        max_fall = max(max_fall, potential_fall)

        # Обновляем минимум, если нашли новый
        max_oi = max(value, max_oi)
        min_oi = min(value, min_oi)

    grow_p = max_growth / min_oi
    fall_p = max_fall / max_oi
    return grow_p, fall_p


def oi_up_down_handler(percent: float, timeframe: int):
    async def func(symbol: Symbol):
        grow_p, fall_p = get_oi_change(percent, timeframe)
        change = grow_p if percent > 0 else fall_p

        logger.info(f"{symbol.symbol} change {change}")
        if change >= abs(percent):
            if symbol.last_alert > 0:
                symname = symbol.symbol.split(":")[0]
                template = env.get_template("oi_signal.jinja2")
                await send_signal(template.render(symname=symname, change=change))

            symbol.last_alert = 0
        else:
            symbol.last_alert += 1

    return func


async def main_pattern_handler(symbol: Symbol):
    """
    1 | Проверяешь, выросла ли цена

    На +2.5 процента или больше за последние 10 минут

    На +7 процентов или больше за последние 20 минут

    2 | Проверяешь рост OI (открытого интереса)

    На +2 процента или больше за последние 10 минут

    На +4 процента или больше за последние 20 минут
    """
    price_up_10 = get_change_price(symbol, 10)[0]

    price_up_20 = get_change_price(symbol, 20)[0]

    oi_up_10 = get_oi_change(symbol, 10)[0]
    oi_up_20 = get_oi_change(symbol, 20)[0]

    if (price_up_10 >= 0.025 and price_up_20 >= 0.07) and (oi_up_10 >= 0.02 and oi_up_20 >= 0.04):
        logger.info(f"{symbol.symbol} - main_pattern")
        if symbol.last_alert > 0:
            symname = symbol.symbol.split(":")[0]
            template = env.get_template("pattern_signal.jinja2")
            await send_signal(template.render(symname=symname))

            symbol.last_alert = 0
        else:
            symbol.last_alert += 1
