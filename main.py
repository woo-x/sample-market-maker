import atexit
import concurrent.futures
import logging
import queue
import signal
import sys
import threading
import time
import typing

import settings
from decimal import Decimal
from woo_x.client import Client
from woo_x.orderbook import Orderbook
from woo_x.types import ws, rest

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s.%(msecs)s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)


class OrderManager:
    orderbook: Orderbook | None
    positions: dict[str, typing.Tuple[float, float]] = {}  # (holding, last_updated)
    balances: dict[str, typing.Tuple[float, float]] = {}  # (holding, last_updated)

    def __init__(self):
        atexit.register(self.exit)
        signal.signal(signal.SIGTERM, self.exit)

        self.client = Client(
            environment=settings.environment,
            application_id=settings.application_id,
            public_api_key=settings.public_api_key,
            secret_api_key=settings.secret_api_key,
        )

        self.exchange_information = self.client.exchange_information(settings.symbol)
        self.orderbook = None
        self.initial_positions_snapshot = threading.Event()
        self.initial_balances_snapshot = threading.Event()

        def track_orderbook():
            for orderbook in self.client.orderbooks(settings.symbol):
                self.orderbook = orderbook

        def track_own_orders():
            for executionreport in self.client.executionreport():
                match executionreport["data"]["status"]:
                    case "NEW":
                        logging.info(
                            f"Order placed (#{executionreport['data']['orderId']}): {executionreport['data']['side']} {executionreport['data']['price'], executionreport['data']['quantity']}"
                        )
                    case "CANCELLED":
                        logging.info(
                            f"Order cancelled (#{executionreport['data']['orderId']}): {executionreport['data']['side']} {executionreport['data']['price'], executionreport['data']['quantity']}"
                        )
                    case "PARTIAL_FILLED" | "FILLED":
                        logging.info(
                            f"Order filled (#{executionreport['data']['orderId']}): {executionreport['data']['side']} {executionreport['data']['executedQuantity']} @ {executionreport['data']['executedPrice']}"
                        )

        def track_position_changes():
            q = queue.Queue()

            class Message(typing.TypedDict):
                is_snapshot: bool
                positions: dict[str, typing.Tuple[float, float]]

            def consume_initial_snapshot():
                snapshot = self.client.get_all_position_info()

                message: Message = {
                    "is_snapshot": True,
                    "positions": {
                        position["symbol"]: (
                            position["holding"],
                            int(position["timestamp"] * 1e3),
                        )
                        for position in snapshot["data"]["positions"]
                    },
                }

                q.put_nowait(message)

            def consume_incremental_updates():
                for position in self.client.position():
                    message: Message = {
                        "is_snapshot": False,
                        "positions": {
                            symbol: (data["holding"], position["ts"])
                            for symbol, data in position["data"]["positions"].items()
                        },
                    }

                    q.put_nowait(message)

            threading.Thread(target=consume_initial_snapshot, daemon=True).start()
            threading.Thread(target=consume_incremental_updates, daemon=True).start()

            while True:
                message: Message = q.get()

                for symbol, position in message["positions"].items():
                    if symbol not in self.positions:
                        self.positions[symbol] = position
                    else:
                        if position[1] > self.positions[symbol][1]:
                            self.positions[symbol] = position

                if message["is_snapshot"]:
                    self.initial_positions_snapshot.set()

        def track_balance_changes():
            q = queue.Queue()

            class Message(typing.TypedDict):
                is_snapshot: bool
                balances: dict[str, typing.Tuple[float, float]]

            def consume_initial_snapshot():
                snapshot = self.client.get_current_holding()

                message: Message = {
                    "is_snapshot": True,
                    "balances": {
                        datum["token"]: (datum["holding"], snapshot["timestamp"])
                        for datum in snapshot["data"]["holding"]
                    },
                }

                q.put_nowait(message)

            def consume_incremental_updates():
                for balance in self.client.balance():
                    message: Message = {
                        "is_snapshot": False,
                        "balances": {
                            symbol: (data["holding"], balance["ts"])
                            for symbol, data in balance["data"]["balances"].items()
                        },
                    }

                    q.put_nowait(message)

            threading.Thread(target=consume_initial_snapshot, daemon=True).start()
            threading.Thread(target=consume_incremental_updates, daemon=True).start()

            while True:
                message: Message = q.get()

                for symbol, holding in message["balances"].items():
                    if symbol not in self.balances:
                        self.balances[symbol] = holding
                    else:
                        if holding[1] > self.balances[symbol][1]:
                            self.balances[symbol] = holding

                if message["is_snapshot"]:
                    self.initial_balances_snapshot.set()

        threading.Thread(target=track_orderbook, daemon=True).start()
        threading.Thread(target=track_own_orders, daemon=True).start()
        threading.Thread(target=track_position_changes, daemon=True).start()
        threading.Thread(target=track_balance_changes, daemon=True).start()

    def readiness(self):
        return {
            "orderbook": self.orderbook is not None,
            "positions": self.initial_positions_snapshot.is_set(),
            "balances": self.initial_balances_snapshot.is_set(),
        }

    def ready(self):
        return all(self.readiness().values())

    def quotes(self):
        messages: typing.List[rest.SendOrderParams] = []

        def send_order_params(i) -> rest.SendOrderParams:
            def price(i):
                [[bid_price, _], [ask_price, _]] = self.orderbook.bbo()

                pivot = bid_price if i < 0 else ask_price

                return float(
                    Decimal(str(pivot * (1 + settings.spread) ** i)).quantize(
                        Decimal(str(self.exchange_information["info"]["quote_tick"]))
                    )
                )

            def quantity(i):
                return 0.001

            return {
                "symbol": settings.symbol,
                "side": typing.cast(
                    typing.Literal["BUY", "SELL"], "BUY" if i < 0 else "SELL"
                ),
                "order_type": "LIMIT",
                "order_price": price(i),
                "order_quantity": quantity(i),
            }

        for i in reversed(range(1, settings.count + 1)):
            messages.append(send_order_params(i))
            messages.append(send_order_params(-i))

        return messages

    def loop(self):
        while not self.ready():
            logging.info(
                f"Some components aren't ready just yet, skipping tick: {self.readiness()}"
            )

            time.sleep(1)

        try:
            while True:
                logging.info("--------------------------------")
                logging.info(f"Positions: {[(symbol, datum[0]) for symbol, datum in self.positions.items()]}")
                logging.info(f"Balances: {[(symbol, datum[0]) for symbol, datum in self.balances.items()]}")
                logging.info(f"{settings.symbol} BBO: {self.orderbook.bbo()}")
                logging.info("--------------------------------")

                self.client.cancel_orders(settings.symbol)

                with concurrent.futures.ThreadPoolExecutor() as executor:
                    [
                        executor.submit(self.client.send_order, send_order_params)
                        for send_order_params in self.quotes()
                    ]

                time.sleep(settings.wait)
        except (KeyboardInterrupt, SystemExit):
            sys.exit()

    def exit(self):
        logging.info("Shutting down bot...")

        self.client.cancel_orders(settings.symbol)

        logging.info("Shut down bot.")


def main():
    logging.info("Initializing WOO X sample market maker.")

    order_manager = OrderManager()

    order_manager.loop()


if __name__ == "__main__":
    main()
