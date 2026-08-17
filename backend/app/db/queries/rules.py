"""Query helpers for the anomaly rules engine.

This module provides access to the rule definitions for the explainer page.
"""
from __future__ import annotations

from backend.app.core.config import settings


def get_rule_definitions() -> dict:
    """Return the complete anomaly rule definitions from settings.

    These are static constants defined in the config, so no DB query needed.
    """
    return {
        "fuel": {
            "anomaly_threshold": settings.fuel_anomaly_threshold,
            "description": "Fuel expenses flagged if amount exceeds benchmark * (1 + threshold)",
        },
        "toll": {
            "anomaly_threshold": settings.toll_anomaly_threshold,
            "description": "Toll expenses flagged if amount exceeds expected max for route",
        },
        "repair": {
            "anomaly_threshold": settings.repair_anomaly_threshold,
            "description": "Repair expenses flagged if amount exceeds daily max",
        },
        "challan": {
            "anomaly_threshold": settings.challan_anomaly_threshold,
            "description": "Challan/fine expenses flagged if amount exceeds standard fine range",
        },
        "rto_fine": {
            "anomaly_threshold": settings.rto_fine_anomaly_threshold,
            "description": "RTO fine expenses flagged if amount exceeds standard range",
        },
        "def": {
            "anomaly_threshold": settings.def_anomaly_threshold,
            "description": "DEF fluid expenses flagged if amount exceeds expected consumption",
        },
        "other": {
            "anomaly_threshold": settings.other_anomaly_threshold,
            "description": "Other/misc expenses flagged if amount exceeds daily limit",
        },
        "goods_buy": {
            "anomaly_threshold": settings.goods_buy_anomaly_threshold,
            "description": "Goods purchase expenses always pending approval",
        },
        "goods_sale": {
            "anomaly_threshold": settings.goods_sale_anomaly_threshold,
            "description": "Goods sale expenses always pending approval",
        },
    }