# Python API

The synchronous functional API is the shortest path for scripts:

~~~python
import tvfinance

results = tvfinance.search("Apple")
quote = tvfinance.quote("NASDAQ:AAPL")
bars = tvfinance.history("NASDAQ:AAPL", resolution="1D", count=100)
chain = tvfinance.options_chain("NASDAQ:AAPL")
~~~

options_chain discovers the nearest available series when expiration and root
are omitted. Pass both values for deterministic selection.

Use tvfinance.aio in an event loop:

~~~python
from tvfinance import aio

quote = await aio.quote("NASDAQ:AAPL")
async for update in aio.stream_quotes(["NASDAQ:AAPL", "NASDAQ:MSFT"]):
    print(update)
~~~

For repeated calls, prefer Client or AsyncClient so connections and cache state
can be reused. Ticker and AsyncTicker bind operations to one symbol; their
plural counterparts group operations across several symbols.

All symbols must use the EXCHANGE:NAME form.
