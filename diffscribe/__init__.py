"""DiffScribe package exports."""

from .cli import main as cli_main
from .diff_parser import DiffParser
from .llm_summarizer import LLMSummarizer
from .risk_analysis import RiskAnalyzer

__all__ = ["cli_main", "DiffParser", "LLMSummarizer", "RiskAnalyzer"]

__version__ = "0.1.0"
