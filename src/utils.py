"""
Utility functions for the Parallel Web Crawler
"""

import logging
import re
from urllib.parse import urljoin, urlparse, urlunparse
from typing import Set, List, Optional, Dict, Any
from urllib.robotparser import RobotFileParser

def setup_logging(rank: int, level: int = logging.INFO) -> logging.Logger:
    """
    Set up logging for a specific MPI process
    
    Args:
        rank: MPI process rank
        level: Logging level
        
    Returns:
        logging.Logger: Configured logger
    """
    logger = logging.getLogger(f'crawler.rank{rank}')
    logger.setLevel(level)
    
    # Avoid duplicate handlers
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            f'[Rank {rank}] %(asctime)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    return logger

def normalize_url(url: str, base_url: Optional[str] = None) -> Optional[str]:
    """
    Normalize a URL for consistent processing and deduplication
    
    Args:
        url: URL to normalize
        base_url: Base URL for relative URL resolution
        
    Returns:
        str: Normalized URL or None if invalid
    """
    try:
        # Handle relative URLs
        if base_url and not url.startswith(('http://', 'https://')):
            url = urljoin(base_url, url)
        
        # Parse URL
        parsed = urlparse(url.strip())
        
        # Skip non-HTTP(S) URLs
        if parsed.scheme not in ('http', 'https'):
            return None
        
        # Skip empty or invalid URLs
        if not parsed.netloc:
            return None
        
        # Normalize components
        scheme = parsed.scheme.lower()
        netloc = parsed.netloc.lower()
        path = parsed.path
        query = parsed.query
        
        # Remove default ports
        if ':80' in netloc and scheme == 'http':
            netloc = netloc.replace(':80', '')
        elif ':443' in netloc and scheme == 'https':
            netloc = netloc.replace(':443', '')
        
        # Normalize path (remove trailing slash except for root)
        if path.endswith('/') and len(path) > 1:
            path = path.rstrip('/')
        elif not path:
            path = '/'
        
        # Remove fragment (anchor)
        fragment = ''
        
        # Reconstruct normalized URL
        normalized = urlunparse((scheme, netloc, path, '', query, fragment))
        return normalized
        
    except Exception:
        return None

def extract_links_from_html(html_content: str, base_url: str) -> Set[str]:
    """
    Extract and normalize all links from HTML content
    
    Args:
        html_content: HTML content as string
        base_url: Base URL for resolving relative links
        
    Returns:
        Set[str]: Set of normalized URLs
    """
    links = set()
    
    try:
        # Simple regex-based link extraction (more robust than full parsing)
        # This handles various link formats including those in JavaScript
        link_patterns = [
            r'href\s*=\s*["\']([^"\']+)["\']',  # Standard href attributes
            r'<a\s+[^>]*href\s*=\s*["\']([^"\']+)["\']',  # More specific anchor tags
        ]
        
        for pattern in link_patterns:
            matches = re.findall(pattern, html_content, re.IGNORECASE)
            for match in matches:
                # Skip certain types of links
                if any(match.lower().startswith(skip) for skip in [
                    'javascript:', 'mailto:', 'tel:', 'ftp:', 'file:',
                    '#', 'data:', 'blob:'
                ]):
                    continue
                
                # Normalize and add to set
                normalized = normalize_url(match, base_url)
                if normalized:
                    links.add(normalized)
    
    except Exception as e:
        # Log error but don't fail completely
        pass
    
    return links

def is_robots_allowed(url: str, robots_cache: dict, user_agent: str = '*') -> bool:
    """
    Check if a URL is allowed according to robots.txt
    
    Args:
        url: URL to check
        robots_cache: Cache of RobotFileParser objects by domain
        user_agent: User agent string to check against
        
    Returns:
        bool: True if crawling is allowed, False otherwise
    """
    try:
        parsed = urlparse(url)
        domain = f"{parsed.scheme}://{parsed.netloc}"
        
        # Check cache first
        if domain not in robots_cache:
            robots_url = urljoin(domain, '/robots.txt')
            rp = RobotFileParser()
            rp.set_url(robots_url)
            
            try:
                rp.read()
                robots_cache[domain] = rp
            except Exception:
                # If we can't fetch robots.txt, assume allowed
                robots_cache[domain] = None
                return True
        
        robots_parser = robots_cache[domain]
        if robots_parser is None:
            return True
        
        return robots_parser.can_fetch(user_agent, url)
        
    except Exception:
        # On any error, assume allowed
        return True

def get_domain_from_url(url: str) -> Optional[str]:
    """
    Extract domain from URL
    
    Args:
        url: URL to extract domain from
        
    Returns:
        str: Domain or None if invalid URL
    """
    try:
        parsed = urlparse(url)
        return parsed.netloc.lower()
    except Exception:
        return None

def clean_text(text: str, max_length: int = 500) -> str:
    """
    Clean and truncate text content
    
    Args:
        text: Text to clean
        max_length: Maximum length to keep
        
    Returns:
        str: Cleaned text
    """
    if not text:
        return ""
    
    # Remove extra whitespace and newlines
    cleaned = re.sub(r'\s+', ' ', text.strip())
    
    # Truncate if too long
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length] + "..."
    
    return cleaned

def validate_seed_urls(urls: List[str]) -> List[str]:
    """
    Validate and normalize a list of seed URLs
    
    Args:
        urls: List of URLs to validate
        
    Returns:
        List[str]: List of valid normalized URLs
    """
    valid_urls = []
    
    for url in urls:
        normalized = normalize_url(url.strip())
        if normalized:
            valid_urls.append(normalized)
    
    return valid_urls
