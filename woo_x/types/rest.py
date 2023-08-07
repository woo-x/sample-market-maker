import typing
import typing_extensions

# TODO: Add nested TypedDict


class ExchangeInformationResponseInfo(typing.TypedDict):
    symbol: str
    quote_min: float
    quote_max: float
    quote_tick: float
    base_min: float
    base_max: float
    base_tick: float
    min_notional: float
    price_range: float
    price_scope: float
    is_stable: bool
    precisions: typing.List[int]
    created_time: str
    updated_time: str


class ExchangeInformationResponse(typing.TypedDict):
    success: bool
    info: ExchangeInformationResponseInfo


class AvailableSymbolsResponseRow(typing.TypedDict):
    symbol: str
    quote_min: float  # TODO: May be int?
    quote_max: float
    quote_tick: float
    base_min: float
    base_max: float
    base_tick: float
    min_notional: float  # TODO: May be int?
    price_range: float
    price_scope: float
    created_time: float
    updated_time: float
    is_stable: int  # TODO: May be 1 or 0
    is_trading: int  # TODO: May be 1 or 0?
    precisions: typing.List[float]


class AvailableSymbolsResponse(typing.TypedDict):
    success: bool
    rows: typing.List[AvailableSymbolsResponseRow]


class MarketTradesResponseRow(typing.TypedDict):
    symbol: str
    side: typing.Literal["BUY", "SELL"]
    executed_price: float
    executed_quantity: float
    executed_timestamp: str
    source: typing.Literal[0, 1]


class MarketTradesResponse(typing.TypedDict):
    success: bool
    rows: typing.List[MarketTradesResponseRow]


KlineType = typing.Literal[
    "1m", "5m", "15m", "30m", "1h", "4h", "12h", "1d", "1w", "1mon", "1y"
]


class KlineResponseRow(typing.TypedDict):
    open: float
    close: float
    low: float
    high: float
    volume: float
    amount: float
    symbol: str
    type: KlineType
    start_timestamp: int
    end_timestamp: int


class KlineResponse(typing.TypedDict):
    success: bool
    rows: typing.List[KlineResponseRow]


class AvailableTokenResponseRow(typing.TypedDict):
    token: str
    fullname: str
    decimals: int
    delisted: bool
    balance_token: str
    created_time: str
    updated_time: str
    can_collateral: bool
    can_short: bool


class AvailableTokenResponse(typing.TypedDict):
    success: bool
    rows: typing.List[AvailableTokenResponseRow]


class SendOrderParams(typing.TypedDict):
    symbol: str
    client_order_id: typing_extensions.NotRequired[int]
    order_tag: typing_extensions.NotRequired[str]
    order_type: typing.Literal["LIMIT", "MARKET", "IOC", "FOK", "POST_ONLY"]
    order_price: typing_extensions.NotRequired[
        float
    ]  # If order_type is MARKET, then is not required, otherwise this parameter is required.
    order_quantity: typing_extensions.NotRequired[
        float
    ]  # For MARKET/ASK/BID order, if order_amount is given, it is not required.
    order_amount: typing_extensions.NotRequired[
        float
    ]  # For MARKET/ASK/BID order, the order size in terms of quote currency
    reduce_only: typing_extensions.NotRequired[bool]
    side: typing.Literal["SELL", "BUY"]


class SendOrderResponse(typing.TypedDict):  # TODO: Test this against all order types
    success: bool
    timestamp: str
    order_id: int
    order_type: typing.Literal["LIMIT", "MARKET", "IOC", "FOK", "POST_ONLY"]
    order_price: float
    order_quantity: typing.Optional[float]
    order_amount: typing.Optional[float]
    client_order_id: int


class CancelOrderParams(typing.TypedDict):
    symbol: str
    order_id: int


class CancelOrderResponse(typing.TypedDict):
    success: bool
    status: str


class CancelOrderByClientOrderIdParams(typing.TypedDict):
    symbol: str
    client_order_id: int


class CancelOrdersParams(typing.TypedDict):
    symbol: str


class OrderBookSnapshotResponseOrder(typing.TypedDict):
    price: float
    quantity: float


class OrderbookSnapshotResponse(typing.TypedDict):
    success: bool
    timestamp: int
    asks: typing.List[OrderBookSnapshotResponseOrder]
    bids: typing.List[OrderBookSnapshotResponseOrder]


class PositionsResponseDataPosition(typing.TypedDict):
    symbol: str
    holding: float
    pendingLongQty: float
    pendingShortQty: float
    settlePrice: float
    averageOpenPrice: float
    pnl24H: float
    fee24H: float
    markPrice: float
    estLiqPrice: float
    timestamp: float


class PositionsResponseData(typing.TypedDict):
    positions: typing.List[PositionsResponseDataPosition]


class PositionsResponse(typing.TypedDict):
    success: bool
    data: PositionsResponseData
    timestamp: int
