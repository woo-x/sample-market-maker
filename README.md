# WOO X Sample Market Maker

This is a sample market making bot for [WOO X](https://x.woo.org). It provides the following:

* A `Client` wrapper for both REST and WebSocket APIs:
  * Exceptions & reconnections are handled for you.
  * Utility functions for e.g keeping a local orderbook in sync are included.
  * Both request and response data structures have [type hints](https://docs.python.org/3/library/typing.html), such that IDEs like [PyCharm](https://www.jetbrains.com/pycharm/) are able to provide autocompletion and static type checkers like [mypy](https://mypy-lang.org/) can help you catch errors in your code.
* A simple market making strategy as scaffold for your own:
  * Out of the box, it implements order placement by best price on each side, showcasing how to use the `Client` wrapper.
  * Fills and balance & position updates are monitored in real time.
  * More complicated strategies are up to the user - try looking at the utility functions in the [Orderbook](./woo_x/orderbook.py) implementation to define signals, or incorporating data from other markets to catch moves early!

> This code is mainly intended to ease interfacing with the WOO X API - the sample market making strategy is not particularly sophisticated and will likely lose money.


## Getting Started

1. Create a set of API credentials: click [here](https://support.woo.org/hc/en-001/articles/4410291152793--How-do-I-create-the-API-) for instructions  - make sure to check the "Enable Trading" box!
2. Clone this repository:
```shell
git clone git@github.com:woo-x/sample-market-maker.git
cd sample-market-maker
```
3. Create & activate a [virtual environment](https://docs.python.org/3/library/venv.html):
```shell
python -m venv .venv
source ./.venv/bin/activate
pip install -r requirements.txt
```
3. Edit [settings.py](./settings.py) to set your API credentials.
4. Run the market maker:
```shell
python main.py
```


## Notes on API rate limits

By default, the [Send Order](https://docs.woo.org/#send-order) rate limit is 5 requests per 1 symbol per 1 second.

Should this ever become a obstacle, please [reach out to support](https://support.woo.org/hc/en-001) with details of your quoting. We are usually able to raise a user's rate limit without issue.

## Compatibility

This module supports Python 3.10 and later.

## See also

* [WOO X API docs](https://docs.woo.org/#general-information).
