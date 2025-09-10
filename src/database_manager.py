"""
Database management for the Parallel Web Crawler using SQLite
"""

import sqlite3
import threading
from datetime import datetime
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

class DatabaseManager:
    """
    Manages SQLite database operations for the web crawler
    Thread-safe with connection pooling
    """
    
    def __init__(self, db_path: str):
        """
        Initialize database manager
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.lock = threading.Lock()
        self._init_database()
    
    def _init_database(self):
        """Initialize database schema"""
        with self.get_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS crawled_urls (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT UNIQUE NOT NULL,
                    title TEXT,
                    content_length INTEGER DEFAULT 0,
                    status TEXT NOT NULL,
                    depth INTEGER DEFAULT 0,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    domain TEXT,
                    response_time REAL DEFAULT 0.0,
                    error_message TEXT
                )
            ''')
            
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_url ON crawled_urls(url)
            ''')
            
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_domain ON crawled_urls(domain)
            ''')
            
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_status ON crawled_urls(status)
            ''')
            
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_depth ON crawled_urls(depth)
            ''')
            
            # Table for tracking discovered links
            conn.execute('''
                CREATE TABLE IF NOT EXISTS discovered_links (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_url TEXT NOT NULL,
                    target_url TEXT NOT NULL,
                    depth INTEGER NOT NULL,
                    discovered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (source_url) REFERENCES crawled_urls(url)
                )
            ''')
            
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_source_url ON discovered_links(source_url)
            ''')
            
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_target_url ON discovered_links(target_url)
            ''')
            
            conn.commit()
    
    @contextmanager
    def get_connection(self):
        """
        Get a database connection with automatic cleanup
        
        Yields:
            sqlite3.Connection: Database connection
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            conn.row_factory = sqlite3.Row  # Enable dict-like row access
            yield conn
        finally:
            if conn:
                conn.close()
    
    def insert_crawl_result(self, result: Dict[str, Any]) -> bool:
        """
        Insert crawl result into database
        
        Args:
            result: Dictionary containing crawl result data
            
        Returns:
            bool: True if insertion successful, False otherwise
        """
        try:
            with self.lock:
                with self.get_connection() as conn:
                    conn.execute('''
                        INSERT OR REPLACE INTO crawled_urls 
                        (url, title, content_length, status, depth, domain, response_time, error_message)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        result.get('url'),
                        result.get('title'),
                        result.get('content_length', 0),
                        result.get('status'),
                        result.get('depth', 0),
                        result.get('domain'),
                        result.get('response_time', 0.0),
                        result.get('error_message')
                    ))
                    conn.commit()
            return True
        except Exception as e:
            print(f"Database insert error: {e}")
            return False
    
    def insert_discovered_links(self, source_url: str, target_urls: List[str], depth: int) -> bool:
        """
        Insert discovered links into database
        
        Args:
            source_url: URL where links were found
            target_urls: List of discovered URLs
            depth: Depth at which links were discovered
            
        Returns:
            bool: True if insertion successful, False otherwise
        """
        try:
            with self.lock:
                with self.get_connection() as conn:
                    for target_url in target_urls:
                        conn.execute('''
                            INSERT OR IGNORE INTO discovered_links 
                            (source_url, target_url, depth)
                            VALUES (?, ?, ?)
                        ''', (source_url, target_url, depth))
                    conn.commit()
            return True
        except Exception as e:
            print(f"Database link insert error: {e}")
            return False
    
    def url_exists(self, url: str) -> bool:
        """
        Check if URL already exists in database
        
        Args:
            url: URL to check
            
        Returns:
            bool: True if URL exists, False otherwise
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.execute('SELECT 1 FROM crawled_urls WHERE url = ?', (url,))
                return cursor.fetchone() is not None
        except Exception:
            return False
    
    def get_crawl_stats(self) -> Dict[str, Any]:
        """
        Get crawling statistics
        
        Returns:
            Dict[str, Any]: Dictionary with crawling statistics
        """
        try:
            with self.get_connection() as conn:
                stats = {}
                
                # Total URLs crawled
                cursor = conn.execute('SELECT COUNT(*) FROM crawled_urls')
                stats['total_crawled'] = cursor.fetchone()[0]
                
                # Success/error counts
                cursor = conn.execute('''
                    SELECT status, COUNT(*) as count 
                    FROM crawled_urls 
                    GROUP BY status
                ''')
                status_counts = {row['status']: row['count'] for row in cursor.fetchall()}
                stats['status_counts'] = status_counts
                
                # Depth distribution
                cursor = conn.execute('''
                    SELECT depth, COUNT(*) as count 
                    FROM crawled_urls 
                    GROUP BY depth 
                    ORDER BY depth
                ''')
                depth_counts = {row['depth']: row['count'] for row in cursor.fetchall()}
                stats['depth_counts'] = depth_counts
                
                # Domain distribution (top 10)
                cursor = conn.execute('''
                    SELECT domain, COUNT(*) as count 
                    FROM crawled_urls 
                    GROUP BY domain 
                    ORDER BY count DESC 
                    LIMIT 10
                ''')
                domain_counts = {row['domain']: row['count'] for row in cursor.fetchall()}
                stats['top_domains'] = domain_counts
                
                # Total links discovered
                cursor = conn.execute('SELECT COUNT(*) FROM discovered_links')
                stats['total_links_discovered'] = cursor.fetchone()[0]
                
                return stats
                
        except Exception as e:
            print(f"Database stats error: {e}")
            return {}
    
    def export_to_csv(self, csv_path: str) -> bool:
        """
        Export crawled data to CSV file
        
        Args:
            csv_path: Path to output CSV file
            
        Returns:
            bool: True if export successful, False otherwise
        """
        try:
            import csv
            
            with self.get_connection() as conn:
                cursor = conn.execute('''
                    SELECT url, title, content_length, status, depth, timestamp, domain, response_time
                    FROM crawled_urls 
                    ORDER BY timestamp
                ''')
                
                with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
                    writer = csv.writer(csvfile)
                    
                    # Write header
                    writer.writerow([
                        'url', 'title', 'content_length', 'status', 
                        'depth', 'timestamp', 'domain', 'response_time'
                    ])
                    
                    # Write data
                    for row in cursor:
                        writer.writerow(row)
            
            return True
            
        except Exception as e:
            print(f"CSV export error: {e}")
            return False
    
    def cleanup_old_entries(self, days_old: int = 30) -> int:
        """
        Clean up old database entries
        
        Args:
            days_old: Remove entries older than this many days
            
        Returns:
            int: Number of entries removed
        """
        try:
            with self.lock:
                with self.get_connection() as conn:
                    cursor = conn.execute('''
                        DELETE FROM crawled_urls 
                        WHERE timestamp < datetime('now', '-{} days')
                    '''.format(days_old))
                    
                    deleted_count = cursor.rowcount
                    conn.commit()
                    
                    return deleted_count
                    
        except Exception as e:
            print(f"Database cleanup error: {e}")
            return 0
    
    def close(self):
        """Close database connections and cleanup"""
        # SQLite connections are closed automatically by context manager
        pass
