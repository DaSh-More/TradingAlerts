import json
from math import ceil

from jinja2 import Environment, FileSystemLoader
from loguru import logger

from .bot import send_signal
from .db import DB
from .trading import Symbol

env = Environment(loader=FileSystemLoader("./app/templates"))
with open("./app/users.json") as f:
    users = json.load(f)


def get_change_price(symbol: Symbol, timeframe: int, *_):
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
        potential_growth = (current_high - min_price) / min_price
        max_growth = max(max_growth, potential_growth)

        potential_fall = (max_price - current_low) / max_price
        max_fall = max(max_fall, potential_fall)

        # Обновляем минимум, если нашли новый
        max_price = max(current_high, max_price)
        min_price = min(current_low, min_price)

    return max_growth, max_fall


def price_up_down_handler(percent: float, timeframe: int, *_):
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


def get_oi_change(symbol: Symbol, timeframe: int, *_):
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
        potential_growth = (value - min_oi) / min_oi
        max_growth = max(max_growth, potential_growth)

        potential_fall = (max_oi - value) / max_oi
        max_fall = max(max_fall, potential_fall)

        # Обновляем минимум, если нашли новый
        max_oi = max(value, max_oi)
        min_oi = min(value, min_oi)

    return max_growth, max_fall


def oi_up_down_handler(percent: float, timeframe: int, *_):
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


async def main_pattern_handler(symbol: Symbol, db: DB):
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
    is_price_up_10 = price_up_10 >= 0.025
    is_price_up_20 = price_up_20 >= 0.07
    is_oi_up_10 = oi_up_10 >= 0.02
    is_oi_up_20 = oi_up_20 >= 0.04
    
    if is_signal := (is_price_up_10 + is_price_up_20 + is_oi_up_10 + is_oi_up_20):
        template = env.get_template("pattern_signal_db.jinja2")
        db.add_alert(symbol.symbol, template.render, 'green' if is_signal == 4 else "white")

    if is_price_up_10 + is_price_up_20 + is_oi_up_10 + is_oi_up_20 >= 3:
        logger.info(f"{symbol.symbol} - main_pattern")
        if symbol.last_alert > 0:
            symname = symbol.symbol.split(":")[0]
            template = env.get_template("pattern_signal.jinja2")
            await send_signal(
                template.render(
                    symname=symname,
                    oi10=oi_up_10,
                    oi20=oi_up_20,
                    price10=price_up_10,
                    price20=price_up_20,
                    is10oi=is_oi_up_10,
                    is20oi=is_oi_up_20,
                    is10price=is_price_up_10,
                    is20price=is_price_up_20,
                ),
                users=users,
            )

            symbol.last_alert = 0
        else:
            symbol.last_alert += 1
