import typing
import sortedcontainers
import operator


class Orderbook:
    def __init__(
        self,
        bids: typing.List[typing.Tuple[float, float]],
        asks: typing.List[typing.Tuple[float, float]],
        timestamp: int,
    ):
        self.bids = sortedcontainers.SortedDict(operator.neg)
        self.asks = sortedcontainers.SortedDict()
        self.timestamp = timestamp

        if bids:
            self.bids.update({price: size for price, size in bids})

        if asks:
            self.asks.update({price: size for price, size in asks})

    def bbo(
        self,
    ) -> typing.Tuple[typing.Tuple[float, float], typing.Tuple[float, float]]:
        # TODO: Handle items maybe not existing - unlikely but still possible
        return self.bids.peekitem(0), self.asks.peekitem(0)


    def impact_price_spread(self, notional):
        def weighted_average_fill_price(orders) -> float | None:
            filled = 0

            executions = {}

            for price, size in orders:
                fillable = price * size

                if filled + fillable > notional:
                    executions[price] = notional - filled

                    break

                executions[price] = fillable

                filled += fillable
            else:  # Loop completed without breaking i.e not enough liquidity
                return None

            avg_fill_price = sum([price * quantity for price, quantity in executions.items()]) / notional

            return avg_fill_price

        weighted_average_sell_price = weighted_average_fill_price(self.bids.items())

        weighted_average_buy_price = weighted_average_fill_price(self.asks.items())

        if not all([weighted_average_buy_price, weighted_average_sell_price]):
            return None

        spread = (weighted_average_buy_price - weighted_average_sell_price) / weighted_average_buy_price

        return spread

    def depth_within_distance(self, distance):
        bid_price, bid_size = self.bids.peekitem(0)

        ask_price, ask_size = self.asks.peekitem(0)

        mid_price = (bid_price + ask_price) / 2

        upper_bound = mid_price + (mid_price * distance)

        lower_bound = mid_price - (mid_price * distance)

        depth = 0

        for price, size in self.bids.items():
            if price < lower_bound:
                break

            depth += price * size

        for price, size in self.asks.items():
            if price > upper_bound:
                break

            depth += price * size

        return depth
