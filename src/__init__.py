"""
Parallel Web Crawler with MPI
"""

__version__ = "1.0.0"
__author__ = "Parallel Web Crawler Team"

from .config import CrawlerConfig
from .crawler_core import CrawlerCore
from .database_manager import DatabaseManager
from .mpi_coordinator import MPICoordinator
from .utils import setup_logging

__all__ = [
    'CrawlerConfig',
    'CrawlerCore', 
    'DatabaseManager',
    'MPICoordinator',
    'setup_logging'
]
