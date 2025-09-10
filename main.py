#!/usr/bin/env python3
"""
Main entry point for the Parallel Web Crawler with MPI
"""

import sys
import time
import signal
from mpi4py import MPI

from src.crawler_core import CrawlerCore
from src.mpi_coordinator import MPICoordinator
from src.database_manager import DatabaseManager
from src.config import CrawlerConfig
from src.utils import setup_logging

def signal_handler(signum, frame):
    """Handle graceful shutdown on SIGINT"""
    print(f"\nProcess {MPI.COMM_WORLD.Get_rank()} received interrupt signal. Shutting down gracefully...")
    sys.exit(0)

def main():
    """Main entry point for the parallel web crawler"""
    # Set up signal handling
    signal.signal(signal.SIGINT, signal_handler)
    
    # Initialize MPI
    comm = MPI.COMM_WORLD
    rank = comm.Get_rank()
    size = comm.Get_size()
    
    # Validate MPI setup
    if size < 2:
        if rank == 0:
            print("Error: At least 2 processes required (1 master + 1 worker)")
            print("Usage: mpiexec -n <num_processes> python main.py")
        return 1
    
    # Set up logging
    logger = setup_logging(rank)
    
    # Load configuration
    config = CrawlerConfig()
    
    logger.info(f"Process {rank} starting (total processes: {size})")
    
    start_time = time.time()
    
    try:
        # Initialize components
        db_manager = DatabaseManager(config.database_path) if rank == 0 else None
        crawler_core = CrawlerCore(config)
        coordinator = MPICoordinator(comm, rank, size, config, logger)
        
        # Run the appropriate process
        if rank == 0:
            # Master process
            logger.info(f"Master process starting with {size-1} workers")
            coordinator.run_master(db_manager, crawler_core)
        else:
            # Worker process
            logger.info(f"Worker {rank} ready for work")
            coordinator.run_worker(crawler_core)
            
    except KeyboardInterrupt:
        logger.info(f"Process {rank} interrupted by user")
        return 0
    except Exception as e:
        logger.error(f"Process {rank} encountered error: {e}")
        return 1
    finally:
        # Ensure all processes synchronize before exit
        try:
            comm.Barrier()
        except:
            pass
    
    if rank == 0:
        end_time = time.time()
        logger.info(f"Total crawling time: {end_time - start_time:.2f} seconds")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
