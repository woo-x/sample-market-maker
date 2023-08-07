import typing


class ExecutionReportData(typing.TypedDict):
    symbol: str
    clientOrderId: int
    orderId: int
    type: typing.Literal["LIMIT", "MARKET", "IOC", "FOK", "POST_ONLY", "LIQUIDATE"]
    side: typing.Literal["BUY", "SELL"]
    quantity: float
    price: float
    tradeId: int
    executedPrice: float
    executedQuantity: float
    fee: float
    feeAsset: str
    totalExecutedQuantity: float
    avgPrice: float
    status: typing.Literal[
        "NEW",
        "CANCELLED",
        "PARTIAL_FILLED",
        "FILLED",
        "REJECTED",
        "INCOMPLETE",
        "COMPLETED",
    ]
    reason: str
    orderTag: str
    totalFee: float
    visible: float
    timestamp: int
    reduceOnly: bool
    maker: bool


class ExecutionReport(typing.TypedDict):
    topic: str
    ts: int
    data: ExecutionReportData


class PositionDataPosition(typing.TypedDict):
    holding: float
    pendingLongQty: float
    pendingShortQty: float
    averageOpenPrice: float
    pnl24H: float
    fee24H: float
    settlePrice: float
    markPrice: float
    version: int
    openingTime: int
    pnl24HPercentage: float


class PositionData(typing.TypedDict):
    positions: dict[
        str, PositionDataPosition
    ]  # TODO: Be able to do Position['PERP_BTC_USDT'] and have a single key defined for that


class Position(typing.TypedDict):
    topic: typing.Literal["position"]
    ts: int
    data: PositionData


class BBOData(typing.TypedDict):
    symbol: str
    ask: float
    askSize: float
    bid: float
    bidSize: float


class BBO(typing.TypedDict):
    topic: str
    ts: int
    data: BBOData


class BBOs(typing.TypedDict):
    topic: str
    ts: int
    data: typing.List[BBOData]


class TradeData(typing.TypedDict):
    symbol: str
    price: float
    size: float
    side: str
    source: int


class Trade(typing.TypedDict):
    topic: str
    ts: int
    data: TradeData


class MarkPriceData(typing.TypedDict):
    symbol: str
    price: float


class MarkPrice(typing.TypedDict):
    topic: str
    ts: int
    data: MarkPriceData


class IndexPriceData(typing.TypedDict):
    symbol: str
    price: float


class IndexPrice(typing.TypedDict):
    topic: str
    ts: int
    data: IndexPriceData


class OpenInterestData(typing.TypedDict):
    symbol: str
    openInterest: float


class OpenInterest(typing.TypedDict):
    topic: str
    ts: int
    data: OpenInterestData


class EstFundingRateData(typing.TypedDict):
    symbol: str
    fundingRate: float
    fundingTs: int


class EstFundingRate(typing.TypedDict):
    topic: str
    ts: int
    data: EstFundingRateData


class TickerData(typing.TypedDict):
    symbol: str
    open: float
    close: float
    high: float
    low: float
    volume: float
    amount: float
    count: int


class Ticker(typing.TypedDict):
    topic: str
    ts: int
    data: TickerData


class Tickers(typing.TypedDict):
    topic: str
    ts: int
    data: typing.List[TickerData]


class OrderbookData(typing.TypedDict):
    symbol: str
    asks: typing.List[typing.List[float]]
    bids: typing.List[typing.List[float]]


class Orderbook(typing.TypedDict):
    topic: str
    ts: int
    data: OrderbookData


class OrderbookUpdateData(typing.TypedDict):
    symbol: str
    prevTs: int
    asks: typing.List[typing.List[float]]
    bids: typing.List[typing.List[float]]


class OrderbookUpdate(typing.TypedDict):
    topic: str
    ts: int
    data: OrderbookUpdateData

class BalanceDataBalance(typing.TypedDict):
    holding: float
    frozen: float
    interest: float
    pendingShortQty: float
    pendingExposure: float
    pendingLongQty: float
    pendingLongExposure: float
    version: int
    staked: float
    unbonding: float
    vault: float
    averageOpenPrice: float
    pnl24H: float
    fee24H: float
    markPrice: float
    pnl24HPercentage: float

class BalanceData(typing.TypedDict):
    balances: dict[str, BalanceDataBalance]

class Balance(typing.TypedDict):
    topic: typing.Literal["balance"]
    ts: int
    data: BalanceData

class AuthRequestParams(typing.TypedDict):
    apikey: str
    sign: str
    timestamp: str

class AuthRequest(typing.TypedDict):
    id: str
    event: typing.Literal["auth"]
    params: AuthRequestParams

class AuthResponse(typing.TypedDict):
    id: str
    event: typing.Literal["auth"]
    success: bool
    ts: int