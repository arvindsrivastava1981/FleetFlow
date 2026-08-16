"""Server-rendered HTML presentation layer.

Formerly the giant f-strings in `fleetflow_interactive_demo.py` + the
`render_header/footer/sidebar` chrome in `utils.py`.

- chrome.py     : render_header(), render_footer(), render_sidebar()
- dashboard.py  : savings-dashboard page + Chart.js data
- trips.py      : trip listing + new-trip form
- expenses.py   : driver/manager chat threads + ledger table
- settlement.py : settled-pdfs list
- benchmarks.py : fuel-benchmark CRUD page
- rules.py      : rule-engine explainer
All dynamic values are passed through `html.escape()` (fixes stored-XSS).
"""