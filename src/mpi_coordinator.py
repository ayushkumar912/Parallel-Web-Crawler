"""
MPI Coordinator for the Parallel Web Crawler
Handles master-worker coordination and communication
"""

import time
import logging
from typing import Set, List, Dict, Any, Optional, Tuple
from collections import defaultdict, deque
from mpi4py import MPI
from urllib.parse import urlparse

from .utils import normalize_url, validate_seed_urls, get_domain_from_url
from .config import CrawlerConfig
from .database_manager import DatabaseManager
from .crawler_core import CrawlerCore

class WorkItem:
    """Represents a work item for crawling"""
    def __init__(self, url: str, depth: int):
        self.url = url
        self.depth = depth
        self.timestamp = time.time()

class MPICoordinator:
    """
    Coordinates MPI processes for distributed web crawling
    """
    
    def __init__(self, comm: MPI.Comm, rank: int, size: int, config: CrawlerConfig, logger: logging.Logger):
        """
        Initialize MPI coordinator
        
        Args:
            comm: MPI communicator
            rank: Process rank
            size: Total number of processes
            config: Crawler configuration
            logger: Logger instance
        """
        self.comm = comm
        self.rank = rank
        self.size = size
        self.config = config
        self.logger = logger
        
        # Master-specific data structures
        if rank == 0:
            self.visited_urls: Set[str] = set()
            self.work_queue: deque = deque()
            self.active_workers: Set[int] = set()
            self.domain_counts: Dict[str, int] = defaultdict(int)
            self.total_processed = 0
            self.start_time = time.time()
    
    def run_master(self, db_manager: DatabaseManager, crawler_core: CrawlerCore):
        """
        Run the master process
        
        Args:
            db_manager: Database manager instance
            crawler_core: Crawler core instance
        """
        self.logger.info(f"Master process starting with {self.size-1} workers")
        
        try:
            # Load and validate seed URLs
            seed_urls = self._load_seed_urls()
            if not seed_urls:
                self.logger.error("No valid seed URLs found")
                self._terminate_all_workers()
                return
            
            self.logger.info(f"Loaded {len(seed_urls)} seed URLs")
            
            # Initialize work queue with seed URLs
            for url in seed_urls:
                if url not in self.visited_urls:
                    self.work_queue.append(WorkItem(url, 0))
                    self.visited_urls.add(url)
            
            # Track statistics
            urls_sent = 0
            results_received = 0
            
            # Initial work distribution
            for worker_rank in range(1, min(self.size, len(self.work_queue) + 1)):
                if self.work_queue:
                    work_item = self.work_queue.popleft()
                    self.comm.send(work_item, dest=worker_rank, tag=0)
                    self.active_workers.add(worker_rank)
                    urls_sent += 1
                    self.logger.info(f"Sent initial URL to worker {worker_rank}: {work_item.url}")
            
            # Main coordination loop
            while results_received < urls_sent or self.work_queue:
                # Receive results from any worker
                status = MPI.Status()
                result = self.comm.recv(source=MPI.ANY_SOURCE, tag=1, status=status)
                worker_rank = status.Get_source()
                results_received += 1
                
                # Process result
                self._process_result(result, db_manager)
                
                # Send next work item if available
                if self.work_queue:
                    work_item = self.work_queue.popleft()
                    self.comm.send(work_item, dest=worker_rank, tag=0)
                    urls_sent += 1
                    self.logger.info(f"Sent URL to worker {worker_rank}: {work_item.url} (depth {work_item.depth})")
                else:
                    # No more work, remove from active workers
                    self.active_workers.discard(worker_rank)
                    
                    # Send termination signal if no more work
                    if not self.work_queue and worker_rank in self.active_workers:
                        self.comm.send(None, dest=worker_rank, tag=0)
                
                # Log progress periodically
                if results_received % 10 == 0:
                    self._log_progress(results_received, urls_sent)
            
            # Terminate all workers
            self._terminate_all_workers()
            
            # Final statistics
            self._log_final_stats(db_manager)
            
        except Exception as e:
            self.logger.error(f"Master process error: {e}")
            self._terminate_all_workers()
    
    def run_worker(self, crawler_core: CrawlerCore):
        """
        Run a worker process
        
        Args:
            crawler_core: Crawler core instance
        """
        self.logger.info(f"Worker {self.rank} ready for work")
        
        urls_processed = 0
        
        try:
            while True:
                # Receive work item from master
                work_item = self.comm.recv(source=0, tag=0)
                
                # Check for termination signal
                if work_item is None:
                    self.logger.info(f"Worker {self.rank} received termination signal")
                    break
                
                self.logger.info(f"Worker {self.rank} processing: {work_item.url} (depth {work_item.depth})")
                
                # Crawl the URL
                result = crawler_core.crawl_url(work_item.url, work_item.depth)
                
                # Send result back to master
                self.comm.send(result, dest=0, tag=1)
                
                urls_processed += 1
                self.logger.info(f"Worker {self.rank} completed: {work_item.url} [{result['status']}]")
                
        except Exception as e:
            self.logger.error(f"Worker {self.rank} error: {e}")
        finally:
            self.logger.info(f"Worker {self.rank} finished after processing {urls_processed} URLs")
    
    def _load_seed_urls(self) -> List[str]:
        """
        Load and validate seed URLs from file
        
        Returns:
            List[str]: List of valid seed URLs
        """
        try:
            with open(self.config.urls_file, 'r') as f:
                urls = [line.strip() for line in f if line.strip()]
            
            # Validate and normalize URLs
            valid_urls = validate_seed_urls(urls)
            self.logger.info(f"Validated {len(valid_urls)} out of {len(urls)} seed URLs")
            
            return valid_urls
            
        except FileNotFoundError:
            self.logger.error(f"Seed URLs file not found: {self.config.urls_file}")
            return []
        except Exception as e:
            self.logger.error(f"Error loading seed URLs: {e}")
            return []
    
    def _process_result(self, result: Dict[str, Any], db_manager: DatabaseManager):
        """
        Process crawling result from worker
        
        Args:
            result: Crawling result dictionary
            db_manager: Database manager instance
        """
        self.total_processed += 1
        
        # Store result in database
        db_manager.insert_crawl_result(result)
        
        # Log result
        status = result.get('status', 'unknown')
        url = result.get('url', 'unknown')
        depth = result.get('depth', 0)
        
        if status == 'success':
            self.logger.info(f"Crawled successfully: {url} (depth {depth}, {result.get('content_length', 0)} bytes)")
            
            # Process discovered links if not at max depth
            links = result.get('links', set())
            if links and depth < self.config.max_depth:
                new_links = self._filter_and_add_links(links, depth + 1)
                if new_links:
                    # Store discovered links in database
                    db_manager.insert_discovered_links(url, list(new_links), depth + 1)
                    self.logger.info(f"Added {len(new_links)} new links from {url}")
        else:
            self.logger.warning(f"Crawl failed: {url} - {result.get('error_message', 'Unknown error')}")
        
        # Update domain statistics
        domain = result.get('domain')
        if domain:
            self.domain_counts[domain] += 1
    
    def _filter_and_add_links(self, links: Set[str], depth: int) -> Set[str]:
        """
        Filter discovered links and add valid ones to work queue
        
        Args:
            links: Set of discovered URLs
            depth: Depth for new links
            
        Returns:
            Set[str]: Set of newly added URLs
        """
        new_links = set()
        
        for link in links:
            # Skip if already visited
            if link in self.visited_urls:
                continue
            
            # Check domain limits
            domain = get_domain_from_url(link)
            if domain and self.domain_counts[domain] >= self.config.max_urls_per_domain:
                continue
            
            # Validate URL
            if not self.config.is_url_allowed(link):
                continue
            
            # Add to work queue
            self.work_queue.append(WorkItem(link, depth))
            self.visited_urls.add(link)
            new_links.add(link)
        
        return new_links
    
    def _terminate_all_workers(self):
        """Send termination signals to all workers"""
        for worker_rank in range(1, self.size):
            try:
                self.comm.send(None, dest=worker_rank, tag=0)
            except:
                pass  # Ignore errors during termination
        
        self.logger.info("Termination signals sent to all workers")
    
    def _log_progress(self, results_received: int, urls_sent: int):
        """
        Log current progress
        
        Args:
            results_received: Number of results received
            urls_sent: Number of URLs sent to workers
        """
        elapsed_time = time.time() - self.start_time
        rate = results_received / elapsed_time if elapsed_time > 0 else 0
        
        self.logger.info(
            f"Progress: {results_received} results received, "
            f"{len(self.work_queue)} URLs queued, "
            f"{rate:.2f} URLs/sec"
        )
    
    def _log_final_stats(self, db_manager: DatabaseManager):
        """
        Log final crawling statistics
        
        Args:
            db_manager: Database manager instance
        """
        total_time = time.time() - self.start_time
        
        # Get database statistics
        stats = db_manager.get_crawl_stats()
        
        self.logger.info("=" * 50)
        self.logger.info("CRAWLING COMPLETED")
        self.logger.info("=" * 50)
        self.logger.info(f"Total time: {total_time:.2f} seconds")
        self.logger.info(f"Total URLs processed: {stats.get('total_crawled', 0)}")
        self.logger.info(f"Average rate: {stats.get('total_crawled', 0) / total_time:.2f} URLs/sec")
        
        # Status breakdown
        status_counts = stats.get('status_counts', {})
        for status, count in status_counts.items():
            self.logger.info(f"  {status}: {count}")
        
        # Depth breakdown
        depth_counts = stats.get('depth_counts', {})
        self.logger.info(f"URLs by depth:")
        for depth, count in depth_counts.items():
            self.logger.info(f"  Depth {depth}: {count}")
        
        # Top domains
        top_domains = stats.get('top_domains', {})
        self.logger.info(f"Top domains crawled:")
        for domain, count in list(top_domains.items())[:5]:
            self.logger.info(f"  {domain}: {count}")
        
        self.logger.info(f"Results saved to database: {self.config.database_path}")
        self.logger.info("=" * 50)
