"""Audit & settlement math.

Houses the financial derivation currently in `fleetflow_interactive_demo.py`
(`approved_cash_impact`, `total_flagged`, `net_returnable`, trip profit).

- cash.py  : approved_cash_impact, net cash in hand, goods buy/sale handling
- flags.py : standardise "flagged deduction = REJECTED only" everywhere
             (fixes the MEDIUM double-count in deep_agent_recommendation §2.6)
"""
