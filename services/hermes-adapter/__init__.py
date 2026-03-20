#!/usr/bin/env python3
"""
Hermes Adapter - Zend gateway adapter for Hermes AI gateway.

Provides observe and summarize capabilities for milestone 1.
"""

from .adapter import HermesAdapter, HermesConnection, MinerSnapshot, HermesSummary, HermesCapability

__all__ = [
    'HermesAdapter',
    'HermesConnection',
    'MinerSnapshot',
    'HermesSummary',
    'HermesCapability',
]