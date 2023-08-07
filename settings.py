import typing

environment: typing.Literal["production", "staging"] = "production"

# Create a set of production API credentials by following the instructions
# at https://support.woo.org/hc/en-001/articles/4410291152793--How-do-I-create-the-API-

# Make sure to check the "Enable Trading" box!

application_id: str = ""

public_api_key: str = ""

secret_api_key: str = ""

# PERP_BTC_USDT = BTC-PERP
# SPOT_BTC_USDT = BTC/USDT
symbol: str = "PERP_BTC_USDT"

# How many orders place on each side
# Default maximum is 2 as the API rate limit for Send Order is currently 5 per
# symbol each second
count = 2

# In base currency
size = 0.001

# Spread between best price and between each order in the grid, incremental
spread = 0.001

# How long to wait between quotes
wait = 1