"""
Core web crawling functionality for the Parallel Web Crawler
"""

import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
from typing import Dict, Any, Set, Optional
import urllib3

from .utils import normalize_url, extract_links_from_html, clean_text, get_domain_from_url
from .config import CrawlerConfig

# Suppress SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class CrawlerCore:
    """
    Core web crawling functionality with rate limiting and robots.txt compliance
    """
    
    def __init__(self, config: CrawlerConfig):
        """
        Initialize crawler core
        
        Args:
            config: Crawler configuration
        """
        self.config = config
        self.session = requests.Session()
        self.robots_cache = {}  # Cache for robots.txt parsers
        self.last_request_time = {}  # Track last request time per domain
        
        # Configure session
        self.session.headers.update({
            'User-Agent': config.user_agent
        })
        
        # Configure session settings
        adapter = HTTPAdapter(
            max_retries=Retry(
                total=2,
                backoff_factor=0.5,
                status_forcelist=[500, 502, 503, 504]
            )
        )
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)
    
    def crawl_url(self, url: str, depth: int = 0) -> Dict[str, Any]:
        """
        Crawl a single URL and extract information
        
        Args:
            url: URL to crawl
            depth: Current crawling depth
            
        Returns:
            Dict[str, Any]: Crawling result with metadata
        """
        start_time = time.time()
        domain = get_domain_from_url(url)
        
        # Initialize result structure
        result = {
            'url': url,
            'title': '',
            'content_length': 0,
            'status': 'error',
            'depth': depth,
            'domain': domain,
            'response_time': 0.0,
            'error_message': None,
            'links': set(),
            'timestamp': time.time()
        }
        
        try:
            # Check if URL is allowed by configuration
            if not self.config.is_url_allowed(url):
                result['error_message'] = 'URL blocked by configuration'
                result['status'] = 'blocked'
                return result
            
            # Rate limiting per domain
            self._enforce_rate_limit(domain)
            
            # Check robots.txt compliance
            if self.config.respect_robots_txt and not self._is_robots_allowed(url):
                result['error_message'] = 'Blocked by robots.txt'
                result['status'] = 'robots_blocked'
                return result
            
            # Make HTTP request
            response = self.session.get(
                url,
                timeout=self.config.request_timeout,
                verify=self.config.verify_ssl,
                allow_redirects=True,
                stream=False
            )
            
            # Check for successful response
            response.raise_for_status()
            
            # Extract content information
            content = response.content
            result['content_length'] = len(content)
            
            # Parse HTML content
            if 'text/html' in response.headers.get('content-type', '').lower():
                soup = BeautifulSoup(content, 'html.parser')
                
                # Extract title
                title_tag = soup.find('title')
                if title_tag:
                    result['title'] = clean_text(title_tag.get_text(), max_length=200)
                else:
                    result['title'] = 'No Title Found'
                
                # Extract links if not at max depth
                if depth < self.config.max_depth:
                    try:
                        raw_html = response.text
                        discovered_links = extract_links_from_html(raw_html, url)
                        
                        # Filter and validate links
                        valid_links = set()
                        for link in discovered_links:
                            if self.config.is_url_allowed(link):
                                valid_links.add(link)
                        
                        result['links'] = valid_links
                        
                    except Exception as e:
                        # Link extraction failed, but crawling succeeded
                        result['links'] = set()
            else:
                result['title'] = f'Non-HTML content ({response.headers.get("content-type", "unknown")})'
            
            result['status'] = 'success'
            
        except requests.exceptions.RequestException as e:
            result['error_message'] = f'Request error: {str(e)}'
            result['status'] = 'request_error'
            
        except Exception as e:
            result['error_message'] = f'Parsing error: {str(e)}'
            result['status'] = 'parse_error'
        
        finally:
            result['response_time'] = time.time() - start_time
        
        return result
    
    def _enforce_rate_limit(self, domain: str):
        """
        Enforce rate limiting per domain
        
        Args:
            domain: Domain to check rate limit for
        """
        if domain in self.last_request_time:
            elapsed = time.time() - self.last_request_time[domain]
            if elapsed < self.config.crawl_delay:
                sleep_time = self.config.crawl_delay - elapsed
                time.sleep(sleep_time)
        
        self.last_request_time[domain] = time.time()
    
    def _is_robots_allowed(self, url: str) -> bool:
        """
        Check if URL is allowed by robots.txt
        
        Args:
            url: URL to check
            
        Returns:
            bool: True if allowed, False otherwise
        """
        try:
            from urllib.robotparser import RobotFileParser
            
            parsed = urlparse(url)
            domain = f"{parsed.scheme}://{parsed.netloc}"
            
            # Check cache first
            if domain not in self.robots_cache:
                robots_url = urljoin(domain, '/robots.txt')
                rp = RobotFileParser()
                rp.set_url(robots_url)
                
                try:
                    rp.read()
                    self.robots_cache[domain] = rp
                except Exception:
                    # If we can't fetch robots.txt, assume allowed
                    self.robots_cache[domain] = None
                    return True
            
            robots_parser = self.robots_cache[domain]
            if robots_parser is None:
                return True
            
            return robots_parser.can_fetch(self.config.user_agent.split()[0], url)
            
        except Exception:
            # On any error, assume allowed
            return True
    
    def validate_url(self, url: str) -> bool:
        """
        Validate if a URL should be crawled
        
        Args:
            url: URL to validate
            
        Returns:
            bool: True if URL is valid and should be crawled
        """
        try:
            # Basic URL validation
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                return False
            
            # Check allowed protocols
            if parsed.scheme not in self.config.allowed_protocols:
                return False
            
            # Check configuration rules
            if not self.config.is_url_allowed(url):
                return False
            
            return True
            
        except Exception:
            return False
    
    def get_domain_stats(self) -> Dict[str, int]:
        """
        Get statistics about domains processed
        
        Returns:
            Dict[str, int]: Domain request counts
        """
        return {domain: 1 for domain in self.last_request_time.keys()}
    
    def cleanup(self):
        """Clean up resources"""
        if hasattr(self.session, 'close'):
            self.session.close()
