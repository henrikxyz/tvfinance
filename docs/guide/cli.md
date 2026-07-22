# Command line

The base package includes a JSON CLI with no additional dependency.

~~~bash
tvfinance search Apple
tvfinance quote NASDAQ:AAPL
tvfinance history NASDAQ:AAPL --resolution 1D --count 100
tvfinance option-series NASDAQ:AAPL
tvfinance options NASDAQ:AAPL
tvfinance news NASDAQ:AAPL --body
tvfinance news-markdown NASDAQ:AAPL
tvfinance research NASDAQ:AAPL profile
tvfinance calendar earnings --limit 25
~~~

Output is stable UTF-8 JSON except version and help text. This makes the CLI
suitable for shell pipelines and automation.
