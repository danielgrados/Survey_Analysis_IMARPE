"""Bitácoras 120 kHz: radar de la climatología vs. cruceros y descriptores espaciales de la bitácora de celdas.

    from survey_analysis_imarpe.bitacoras import radar_climatologia, descriptores_celdas
"""
from .radar import radar_climatologia
from .celdas import descriptores_celdas

__all__ = ["radar_climatologia", "descriptores_celdas"]
