import hashlib
import hmac
import json
import time
import typing
from websockets.exceptions import ConnectionClosedError
import websockets.sync.client as websockets
import sortedcontainers
import requests
import threading
from woo_x.types import ws, rest
from woo_x.orderbook import Orderbook


class Environment(typing.TypedDict):
    http: str
    ws_public: str
    ws_private: str


class Environments(typing.TypedDict):
    production: Environment
    staging: Environment


ENVIRONMENTS: Environments = {
    "production": {
        "http": "https://api.woo.org",
        "ws_public": "wss://wss.woo.org/ws/stream/{application_id}",
        "ws_private": "wss://wss.woo.org/v2/ws/private/stream/{application_id}",
    },
    "staging": {
        "http": "https://api.staging.woo.org",
        "ws_public": "wss://wss.staging.woo.org/ws/stream/{application_id}",
        "ws_private": "wss://wss.staging.woo.org/v2/ws/private/stream/{application_id}",
    },
}


class Client:
    environment: typing.Literal[
        "production", "staging"
    ]  # TODO: Make this dynamic based on the keys of Environments
    application_id: str
    public_api_key: str
    secret_api_key: str
    session: requests.Session

    def __init__(
        self,
        environment: typing.Literal[
            "production", "staging"
        ],  # TODO: Make this type check (changing 'staging' to 'stagin' doesn't raise an error)
        application_id: str,
        public_api_key: str,
        secret_api_key: str,
    ):
        self.environment = environment
        self.application_id = application_id
        self.public_api_key = public_api_key
        self.secret_api_key = secret_api_key
        self.session = requests.Session()

    def signature_v1(self, timestamp: str, **kwargs):
        signable = (
            "&".join([f"{key}={value}" for key, value in sorted(kwargs.items())])
            + "|"
            + timestamp
        )

        signature = (
            hmac.new(
                bytes(self.secret_api_key, "utf-8"),
                msg=bytes(signable, "utf-8"),
                digestmod=hashlib.sha256,
            )
            .hexdigest()
            .upper()
        )

        return signature

    def signature_v3(self, timestamp: str, method: str, path: str, **kwargs):
        signable = timestamp + method + path

        if kwargs != {}:
            signable += json.dumps(kwargs)

        signature = (
            hmac.new(
                bytes(self.secret_api_key, "utf-8"),
                msg=bytes(signable, "utf-8"),
                digestmod=hashlib.sha256,
            )
            .hexdigest()
            .upper()
        )

        return signature

    def request(self, method: str, path: str, auth: bool, **kwargs):
        request = requests.Request(
            method, ENVIRONMENTS[self.environment]["http"] + path
        )

        if method in ['POST', 'PUT']:
            request.data = kwargs
        else:
            request.params = kwargs

        if auth:
            timestamp = str(int(time.time() * 1000))

            api_version = path[1:3]

            # TODO: Simplify this flow control
            if api_version == "v1":
                request.headers = {
                    "x-api-key": self.public_api_key,
                    "x-api-signature": self.signature_v1(timestamp, **kwargs),
                    "x-api-timestamp": timestamp,
                    'Content-Type': 'application/x-www-form-urlencoded',
                }
            elif api_version == "v3":
                request.headers = {
                    "x-api-key": self.public_api_key,
                    "x-api-signature": self.signature_v3(
                        timestamp, method, path, **kwargs
                    ),
                    "x-api-timestamp": timestamp,
                    'Content-Type': 'application/json',
                }
            else:
                raise RuntimeError(
                    f"Unrecognized API version {api_version} for URL {path}"
                )

        response = self.session.send(self.session.prepare_request(request))

        if not response.ok:
            raise requests.HTTPError(
                f"{response.status_code} Status Code for URL {response.url}: {response.text}"
            )

        return response.json()

    def public_ws(self, sub_request: dict) -> typing.Iterable[dict]:
        with websockets.connect(
                ENVIRONMENTS[self.environment]["ws_public"].format(
                    application_id=self.application_id
                )
        ) as connection:
            connection.send(json.dumps(sub_request))

            for raw_message in connection:
                message = json.loads(raw_message)

                if 'event' in message:
                    if message['event'] == 'ping':
                        threading.Thread(
                            target=connection.send, args=[json.dumps({"event": "pong"})]
                        ).start()

                        continue

                    if message['event'] == 'subscribe':
                        if not message["success"]:
                            raise RuntimeError(message)

                        continue

                if "data" not in message:
                    continue

                yield message

    def private_ws(self, subscription: dict) -> typing.Iterable[dict]:
        with websockets.connect(
                ENVIRONMENTS[self.environment]["ws_private"].format(
                    application_id=self.application_id
                )
        ) as connection:
            timestamp = str(int(time.time() * 1000))

            auth_request: ws.AuthRequest = {
                "id": "auth",
                "event": "auth",
                "params": {
                    "apikey": self.public_api_key,
                    "sign": self.signature_v1(timestamp),
                    "timestamp": timestamp,
                },
            }

            connection.send(json.dumps(auth_request))

            connection.send(json.dumps(subscription))

            for raw_message in connection:
                message = json.loads(raw_message)

                if 'event' in message:
                    if message['event'] == 'ping':
                        threading.Thread(
                            target=connection.send, args=[json.dumps({"event": "pong"})]
                        ).start()

                        continue

                    if message['event'] == 'auth':
                        if not message["success"]:
                            raise RuntimeError(message)

                        continue

                    if message['event'] == 'subscribe':
                        if not message["success"]:
                            raise RuntimeError(message)

                        continue

                if "data" not in message:
                    continue

                yield message

    def exchange_information(self, symbol: str) -> rest.ExchangeInformationResponse:
        return self.request("GET", f"/v1/public/info/{symbol}", False)

    def available_symbols(self) -> rest.AvailableSymbolsResponse:
        return self.request("GET", "/v1/public/info", False)

    def market_trades(self, symbol: str, limit: int = 10) -> rest.MarketTradesResponse:
        return self.request(
            "GET", "/v1/public/market_trades", False, symbol=symbol, limit=limit
        )

    # TODO: Market Trades History(Public)

    def orderbook_snapshot(
        self, symbol: str, max_level: int = 5
    ) -> rest.OrderbookSnapshotResponse:
        return self.request(
            "GET", f"/v1/public/orderbook/{symbol}?max_level={max_level}", False
        )

    def kline(
        self, symbol: str, type: rest.KlineType, limit: int = 100
    ) -> rest.KlineResponse:
        return self.request(
            "GET", "/v1/public/kline", False, symbol=symbol, type=type, limit=limit
        )

    # TODO: Kline - Historical Data

    def available_token(self) -> rest.AvailableTokenResponse:
        return self.request("GET", "/v1/public/token", False)

    def token_network(self):
        return self.request("GET", "/v1/public/token_network", False)

    def predicted_funding_rate_for_all_markets(self):
        return self.request("GET", "/v1/public/funding_rates", False)

    def predicted_funding_rate_for_one_market(self, symbol: str):
        return self.request("GET", f"/v1/public/funding_rate/{symbol}", False)

    def futures_info_for_all_markets(self):
        return self.request("GET", "/v1/public/futures", False)

    def futures_info_for_one_market(self, symbol: str):
        return self.request("GET", f"/v1/public/futures/{symbol}", False)

    def token_config(self):
        return self.request("GET", "/v1/client/token", False)

    def send_order(self, content: rest.SendOrderParams) -> rest.SendOrderResponse:
        return self.request("POST", "/v1/order", True, **content)

    def cancel_order(self, content: rest.CancelOrderParams) -> rest.CancelOrderResponse:
        return self.request("DELETE", "/v1/order", True, **content)

    def cancel_order_by_client_order_id(self, client_order_id: int, symbol: str):
        return self.request(
            "DELETE",
            "/v1/client/order",
            True,
            client_order_id=client_order_id,
            symbol=symbol,
        )

    def cancel_orders(self, symbol: str):
        return self.request("DELETE", "/v1/orders", True, symbol=symbol)

    def cancel_all_pending_orders(self):
        return self.request("DELETE", "/v3/orders/pending", True)

    def get_order(self, oid: int):
        return self.request("GET", f"/v1/order/{oid}", True)

    def get_order_by_client_order_id(self, client_order_id: int):
        return self.request("GET", f"/v1/client/order/{client_order_id}", True)

    def get_orders(self):
        return self.request("GET", f"/v1/orders", True)

    def edit_order(self, order_id: int, price: str, quantity: str):
        return self.request(
            "PUT", f"/v3/order/{order_id}", True, price=price, quantity=quantity
        )

    def edit_order_by_client_order_id(
        self, client_order_id: int, price: str, quantity: str
    ):
        return self.request(
            "PUT",
            f"/v3/order/client/{client_order_id}",
            True,
            **{"price": price, "quantity": quantity},
        )

    # TODO: Algo orders CRUD

    def get_trade(self, tid: int):
        return self.request("GET", f"/v1/client/trade/{tid}", True)

    def get_trades(self, oid: int):
        return self.request("GET", f"/v1/order/{oid}/trades", True)

    def get_trade_history(self, **kwargs):
        return self.request('GET', '/v1/client/trades', True, **kwargs)

    def get_archived_trade_history(self, **kwargs):
        return self.request('GET', '/v1/client/hist_trades', True, **kwargs)

    def get_staking_yield_history(self, **kwargs):
        return self.request('GET', '/v1/staking/yield_history', True, **kwargs)

    def get_current_holding(self):
        return self.request("GET", "/v3/balances", True)

    def get_account_information(self):
        return self.request("GET", "/v3/accountinfo", True)

    def get_token_history(self, **kwargs):
        return self.request('GET', '/v1/client/transaction_history', True, **kwargs)

    def get_account_api_key_and_permission(self):
        return self.request("GET", "/usercenter/api/enabled_credential", True)

    def get_buying_power(self, symbol: str):
        return self.request("GET", "/v3/buypower", True, symbol=symbol)

    def get_token_deposit_address(self, token: str):
        return self.request("GET", "/v1/asset/deposit", True, token=token)

    def token_withdraw(self, **kwargs):
        return self.request('POST', '/v1/asset/withdraw', True, **kwargs)

    def cancel_withdrawal_request(self, **kwargs):
        return self.request('DELETE', '/v1/asset/withdraw', True, **kwargs)

    def asset_history(self, **kwargs):
        return self.request('GET', '/v1/asset/history', True, **kwargs)

    def get_margin_interest_rates(self):
        return self.request('GET', f"/v1/token_interest", True)

    def get_margin_interest_rate_of_token(self, token: str):
        return self.request('GET', f"/v1/token_interest/{token}", True)

    def get_interest_history(self, **kwargs):
        return self.request('GET', '/v1/interest/history', True, **kwargs)
    def repay_interest(self, **kwargs):
        return self.request('POST', '/v1/interest/repay', True, **kwargs)

    def get_referral_reward_history(self, **kwargs):
        return self.request('GET', '/v3/referral_rewards', True, **kwargs)

    def get_subaccounts(self):
        return self.request('GET', '/v1/sub_account/all', True)

    def get_asset_details_from_a_subaccount(self, **kwargs):
        return self.request('GET', '/v1/sub_account/asset_detail', True, **kwargs)

    def get_ip_restriction(self, **kwargs):
        return self.request('GET', '/v1/sub_account/ip_restriction', True, **kwargs)

    def get_transfer_history(self, **kwargs):
        return self.request('GET', '/v1/asset/main_sub_transfer_history', True, **kwargs)
    def transfer_assets(self, **kwargs):
        return self.request('POST', '/v1/asset/main_sub_transfer', True, **kwargs)

    def update_account_mode(self, account_mode: str):
        return self.request('POST', '/v1/client/account_mode', True, account_mode=account_mode)

    def update_leverage_setting(self, leverage: int):
        return self.request('POST', '/v1/client/leverage', True, leverage=leverage)

    def get_funding_fee_history(self, **kwargs):
        return self.request('GET', '/v1/funding_fee/history', True, **kwargs)

    def get_all_position_info(self) -> rest.PositionsResponse:
        return self.request("GET", "/v3/positions", True)

    def orderbook(self, symbol: str) -> typing.Iterable[ws.Orderbook]:
        for message in self.public_ws(
            {
                "id": f"{symbol}@orderbook",
                "topic": f"{symbol}@orderbook",
                "event": "subscribe",
            }
        ):
            yield message

    def orderbookupdate(self, symbol: str) -> typing.Iterable[ws.OrderbookUpdate]:
        for message in self.public_ws(
            {
                "id": f"{symbol}@orderbookupdate",
                "topic": f"{symbol}@orderbookupdate",
                "event": "subscribe",
            }
        ):
            yield message

    def openinterest(self, symbol: str) -> typing.Iterable[ws.OpenInterest]:
        # TODO: raise an error when a non perpetual future symbol is entered
        for message in self.public_ws(
            {
                "id": f"{symbol}@openinterest",
                "topic": f"{symbol}@openinterest",
                "event": "subscribe",
            }
        ):
            yield message

    def markprice(self, symbol: str) -> typing.Iterable[ws.MarkPrice]:
        # TODO: raise an error when a non spot symbol is entered
        for message in self.public_ws(
            {
                "id": f"{symbol}@markprice",
                "topic": f"{symbol}@markprice",
                "event": "subscribe",
            }
        ):
            yield message

    def indexprice(self, symbol: str) -> typing.Iterable[ws.IndexPrice]:
        for message in self.public_ws(
            {
                "id": f"{symbol}@indexprice",
                "topic": f"{symbol}@indexprice",
                "event": "subscribe",
            }
        ):
            yield message

    def trade(self, symbol: str) -> typing.Iterable[ws.Trade]:
        for message in self.public_ws(
            {
                "id": f"{symbol}@trade",
                "topic": f"{symbol}@trade",
                "event": "subscribe",
            }
        ):
            yield message

    def bbo(self, symbol: str) -> typing.Iterable[ws.BBO]:
        for message in self.public_ws(
            {
                "id": f"{symbol}@bbo",
                "topic": f"{symbol}@bbo",
                "event": "subscribe",
            }
        ):
            yield message

    def bbos(self) -> typing.Iterable[ws.BBOs]:
        for message in self.public_ws(
            {
                "id": f"bbos",
                "topic": f"bbos",
                "event": "subscribe",
            }
        ):
            yield message

    def estfundingrate(self, symbol: str) -> typing.Iterable[ws.EstFundingRate]:
        # TODO: raise an error when a non perpetual future symbol is entered
        for message in self.public_ws(
            {
                "id": f"{symbol}@estfundingrate",
                "topic": f"{symbol}@estfundingrate",
                "event": "subscribe",
            }
        ):
            yield message

    def ticker(self, symbol: str) -> typing.Iterable[ws.Ticker]:
        for message in self.public_ws(
            {
                "id": f"{symbol}@ticker",
                "topic": f"{symbol}@ticker",
                "event": "subscribe",
            }
        ):
            yield message

    def tickers(self) -> typing.Iterable[ws.Tickers]:
        for message in self.public_ws(
            {
                "id": f"tickers",
                "topic": f"tickers",
                "event": "subscribe",
            }
        ):
            yield message

    def executionreport(self) -> typing.Iterable[ws.ExecutionReport]:
        for message in self.private_ws(
            {"id": "executionreport", "topic": "executionreport", "event": "subscribe"}
        ):
            yield message

    def position(self) -> typing.Iterable[ws.Position]:
        for message in self.private_ws(
            {"id": "position", "topic": "position", "event": "subscribe"}
        ):
            yield message

    def balance(self) -> typing.Iterable[ws.Balance]:
        for message in self.private_ws(
            {"id": "balance", "topic": "balance", "event": "subscribe"}
        ):
            yield message

    def orderbooks(self, symbol) -> typing.Iterable[Orderbook]:
        def apply(orderbook: Orderbook, orderbookupdate: ws.OrderbookUpdate):
            if orderbook.timestamp != orderbookupdate["data"]["prevTs"]:
                raise ValueError(
                    f"orderbook timestamp {orderbook.timestamp} does not match prevTs {orderbookupdate['data']['prevTs']} in orderbookupdate"
                )

            def delta(
                container: sortedcontainers.SortedDict,
                orders: typing.List[typing.List[float]],
            ):
                for order in orders:
                    price, size = order

                    if size == 0:
                        container.pop(price, None)
                    else:
                        container.update({price: size})

            delta(orderbook.bids, orderbookupdate["data"]["bids"])
            delta(orderbook.asks, orderbookupdate["data"]["asks"])
            orderbook.timestamp = orderbookupdate["ts"]

        while True:
            try:
                orderbook: None | Orderbook = None

                handshook = False

                buffer = []

                aux = {}  # One-time use variable for storing the orderbook snapshot

                def get_orderbook_snapshot():
                    aux["orderbook_snapshot"] = self.orderbook_snapshot(symbol)

                for orderbookupdate in self.orderbookupdate(symbol):
                    if not handshook:
                        threading.Thread(target=get_orderbook_snapshot).start()

                        buffer.append(orderbookupdate)

                        handshook = True

                        continue

                    if "orderbook_snapshot" not in aux:
                        buffer.append(orderbookupdate)

                        continue

                    if orderbook is None:
                        buffer.append(orderbookupdate)

                        orderbook_snapshot = typing.cast(
                            rest.OrderbookSnapshotResponse, aux["orderbook_snapshot"]
                        )

                        orderbook = Orderbook(
                            bids=[
                                (order["price"], order["quantity"])
                                for order in orderbook_snapshot["bids"]
                            ],
                            asks=[
                                (order["price"], order["quantity"])
                                for order in orderbook_snapshot["asks"]
                            ],
                            timestamp=orderbook_snapshot["timestamp"],
                        )

                        for orderbookupdate in buffer:
                            if (
                                orderbookupdate["data"]["prevTs"]
                                >= orderbook_snapshot["timestamp"]
                            ):
                                apply(orderbook, orderbookupdate)

                        continue

                    apply(orderbook, orderbookupdate)

                    yield orderbook
            except ConnectionClosedError:
                continue
