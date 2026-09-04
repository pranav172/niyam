"""NIYAM Growth & Revenue Optimization Module
Implements policy-aware upsell recommendations, authorized cart headroom calculations,
and the 'Save the Sale' 1-Tap Policy Waiver conversion recovery engine.
"""
from services.growth.engine import GrowthEngine, PolicyWaiver, WaiverManager

__all__ = ["GrowthEngine", "PolicyWaiver", "WaiverManager"]
