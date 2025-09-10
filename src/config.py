"""
Configuration management for the Parallel Web Crawler
"""

import os
from dataclasses import dataclass
from typing import Set
from urllib.parse import urlparse

@dataclass
class CrawlerConfig:
    """Configuration settings for the web crawler"""
    
    # Input/Output settings
    urls_file: str = "urls.txt"
    database_path: str = "crawler.db"
    
    # Crawling parameters
    max_depth: int = 2
    crawl_delay: float = 1.0  # seconds between requests per worker
    request_timeout: int = 10  # seconds
    max_urls_per_domain: int = 50
    
    # Request settings
    user_agent: str = "Mozilla/5.0 (compatible; ParallelCrawler/1.0)"
    verify_ssl: bool = False
    max_redirects: int = 5
    
    # Robots.txt compliance
    respect_robots_txt: bool = True
    robots_cache_duration: int = 3600  # seconds
    
    # Allowed file extensions and protocols
    allowed_extensions: Set[str] = None
    blocked_extensions: Set[str] = None
    allowed_protocols: Set[str] = None
    
    def __post_init__(self):
        """Initialize default values after dataclass creation"""
        if self.allowed_extensions is None:
            self.allowed_extensions = {
                '.html', '.htm', '.php', '.asp', '.aspx', '.jsp', 
                '.py', '.rb', '.pl', ''  # empty for pages without extension
            }
        
        if self.blocked_extensions is None:
            self.blocked_extensions = {
                '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
                '.zip', '.rar', '.7z', '.tar', '.gz',
                '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.ico',
                '.mp3', '.mp4', '.wav', '.avi', '.mov', '.wmv',
                '.exe', '.msi', '.deb', '.rpm', '.dmg'
            }
        
        if self.allowed_protocols is None:
            self.allowed_protocols = {'http', 'https'}
    
    def is_url_allowed(self, url: str) -> bool:
        """
        Check if a URL should be crawled based on configuration rules
        
        Args:
            url: The URL to check
            
        Returns:
            bool: True if URL is allowed, False otherwise
        """
        try:
            parsed = urlparse(url.lower())
            
            # Check protocol
            if parsed.scheme not in self.allowed_protocols:
                return False
            
            # Check file extension
            path = parsed.path.lower()
            
            # Check for blocked extensions
            for ext in self.blocked_extensions:
                if path.endswith(ext):
                    return False
            
            # If we have allowed extensions, ensure URL matches one of them
            if self.allowed_extensions:
                if not any(path.endswith(ext) for ext in self.allowed_extensions):
                    # Special case: allow URLs without file extensions
                    if '.' in os.path.basename(path):
                        return False
            
            return True
            
        except Exception:
            return False
    
    @classmethod
    def from_file(cls, config_path: str) -> 'CrawlerConfig':
        """
        Load configuration from a file (future enhancement)
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            CrawlerConfig: Configuration instance
        """
        # For now, return default config
        # TODO: Implement actual file parsing (JSON/YAML)
        return cls()
