#!/usr/bin/env python3
"""
Statistics and analysis tool for the Parallel Web Crawler
"""

import sqlite3
import sys
import argparse
from datetime import datetime
from collections import defaultdict
from urllib.parse import urlparse

def analyze_database(db_path: str):
    """Analyze crawl results and generate detailed statistics"""
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("=" * 60)
        print("PARALLEL WEB CRAWLER - ANALYSIS REPORT")
        print("=" * 60)
        print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Database: {db_path}")
        print()
        
        # Basic statistics
        cursor.execute('SELECT COUNT(*) FROM crawled_urls')
        total_urls = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(DISTINCT domain) FROM crawled_urls')
        unique_domains = cursor.fetchone()[0]
        
        cursor.execute('SELECT AVG(content_length) FROM crawled_urls WHERE status = "success"')
        avg_content_length = cursor.fetchone()[0] or 0
        
        cursor.execute('SELECT SUM(content_length) FROM crawled_urls WHERE status = "success"')
        total_content = cursor.fetchone()[0] or 0
        
        print(f"📊 OVERALL STATISTICS")
        print(f"   Total URLs processed: {total_urls:,}")
        print(f"   Unique domains: {unique_domains:,}")
        print(f"   Average page size: {avg_content_length:.0f} bytes")
        print(f"   Total content crawled: {total_content / (1024*1024):.2f} MB")
        print()
        
        # Status breakdown
        cursor.execute('SELECT status, COUNT(*) FROM crawled_urls GROUP BY status ORDER BY COUNT(*) DESC')
        status_counts = cursor.fetchall()
        
        print(f"📋 STATUS BREAKDOWN")
        for status, count in status_counts:
            percentage = (count / total_urls) * 100
            print(f"   {status:15} {count:6,} ({percentage:5.1f}%)")
        print()
        
        # Depth analysis
        cursor.execute('SELECT depth, COUNT(*), AVG(content_length) FROM crawled_urls GROUP BY depth ORDER BY depth')
        depth_stats = cursor.fetchall()
        
        print(f"📏 DEPTH ANALYSIS")
        for depth, count, avg_size in depth_stats:
            print(f"   Depth {depth}: {count:6,} pages (avg: {avg_size or 0:.0f} bytes)")
        print()
        
        # Top domains
        cursor.execute('''
            SELECT domain, COUNT(*), AVG(content_length), 
                   SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success_count
            FROM crawled_urls 
            WHERE domain IS NOT NULL
            GROUP BY domain 
            ORDER BY COUNT(*) DESC 
            LIMIT 15
        ''')
        domain_stats = cursor.fetchall()
        
        print(f"🌐 TOP DOMAINS CRAWLED")
        print(f"   {'Domain':<30} {'Total':<8} {'Success':<8} {'Avg Size':<10}")
        print(f"   {'-'*30} {'-'*8} {'-'*8} {'-'*10}")
        for domain, total, avg_size, success in domain_stats:
            domain_short = domain[:28] + '..' if len(domain) > 30 else domain
            print(f"   {domain_short:<30} {total:<8,} {success:<8,} {avg_size or 0:<10.0f}")
        print()
        
        # Largest pages
        cursor.execute('''
            SELECT url, title, content_length, depth 
            FROM crawled_urls 
            WHERE status = 'success' AND content_length > 0
            ORDER BY content_length DESC 
            LIMIT 10
        ''')
        largest_pages = cursor.fetchall()
        
        print(f"📄 LARGEST PAGES FOUND")
        for i, (url, title, size, depth) in enumerate(largest_pages, 1):
            title_short = title[:40] + '...' if len(title) > 40 else title
            url_short = url[:50] + '...' if len(url) > 50 else url
            print(f"   {i:2}. [{depth}] {title_short}")
            print(f"       {url_short} ({size:,} bytes)")
        print()
        
        # Error analysis
        cursor.execute('''
            SELECT error_message, COUNT(*) 
            FROM crawled_urls 
            WHERE status != 'success' AND error_message IS NOT NULL
            GROUP BY error_message 
            ORDER BY COUNT(*) DESC 
            LIMIT 10
        ''')
        error_stats = cursor.fetchall()
        
        if error_stats:
            print(f"❌ COMMON ERRORS")
            for error, count in error_stats:
                error_short = error[:60] + '...' if len(error) > 60 else error
                print(f"   {count:4,}x {error_short}")
            print()
        
        # Robots.txt analysis
        cursor.execute("SELECT COUNT(*) FROM crawled_urls WHERE status = 'robots_blocked'")
        robots_blocked = cursor.fetchone()[0]
        
        if robots_blocked > 0:
            print(f"🤖 ROBOTS.TXT COMPLIANCE")
            print(f"   URLs blocked by robots.txt: {robots_blocked:,}")
            
            cursor.execute('''
                SELECT domain, COUNT(*) 
                FROM crawled_urls 
                WHERE status = 'robots_blocked' 
                GROUP BY domain 
                ORDER BY COUNT(*) DESC 
                LIMIT 5
            ''')
            robots_domains = cursor.fetchall()
            
            print(f"   Top domains with robots.txt blocks:")
            for domain, count in robots_domains:
                print(f"     {domain}: {count:,} blocks")
            print()
        
        # Performance metrics
        cursor.execute('''
            SELECT AVG(response_time), MIN(response_time), MAX(response_time)
            FROM crawled_urls 
            WHERE status = 'success' AND response_time > 0
        ''')
        perf_stats = cursor.fetchone()
        
        if perf_stats and perf_stats[0]:
            avg_time, min_time, max_time = perf_stats
            print(f"⚡ PERFORMANCE METRICS")
            print(f"   Average response time: {avg_time:.2f}s")
            print(f"   Fastest response: {min_time:.2f}s")
            print(f"   Slowest response: {max_time:.2f}s")
            print()
        
        # Link discovery stats
        cursor.execute('SELECT COUNT(*) FROM discovered_links')
        total_links = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(DISTINCT target_url) FROM discovered_links')
        unique_links = cursor.fetchone()[0]
        
        if total_links > 0:
            print(f"🔗 LINK DISCOVERY")
            print(f"   Total links discovered: {total_links:,}")
            print(f"   Unique links found: {unique_links:,}")
            print()
        
        conn.close()
        
        print("=" * 60)
        print("Analysis complete!")
        
    except Exception as e:
        print(f"Error analyzing database: {e}")
        return 1
    
    return 0

def export_results(db_path: str, output_format: str = 'csv'):
    """Export crawl results to various formats"""
    
    try:
        conn = sqlite3.connect(db_path)
        
        if output_format == 'csv':
            import csv
            
            output_file = 'crawl_results.csv'
            cursor = conn.cursor()
            cursor.execute('''
                SELECT url, title, content_length, status, depth, timestamp, domain, response_time
                FROM crawled_urls 
                ORDER BY timestamp
            ''')
            
            with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['url', 'title', 'content_length', 'status', 'depth', 'timestamp', 'domain', 'response_time'])
                writer.writerows(cursor.fetchall())
            
            print(f"Results exported to {output_file}")
        
        elif output_format == 'json':
            import json
            
            output_file = 'crawl_results.json'
            cursor = conn.cursor()
            cursor.execute('''
                SELECT url, title, content_length, status, depth, timestamp, domain, response_time
                FROM crawled_urls 
                ORDER BY timestamp
            ''')
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    'url': row[0],
                    'title': row[1],
                    'content_length': row[2],
                    'status': row[3],
                    'depth': row[4],
                    'timestamp': row[5],
                    'domain': row[6],
                    'response_time': row[7]
                })
            
            with open(output_file, 'w', encoding='utf-8') as jsonfile:
                json.dump(results, jsonfile, indent=2, ensure_ascii=False)
            
            print(f"Results exported to {output_file}")
        
        conn.close()
        
    except Exception as e:
        print(f"Error exporting results: {e}")
        return 1
    
    return 0

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Analyze parallel web crawler results')
    parser.add_argument('--db', default='crawler.db', help='Database file path')
    parser.add_argument('--export', choices=['csv', 'json'], help='Export results to file')
    parser.add_argument('--analyze', action='store_true', default=True, help='Show analysis report')
    
    args = parser.parse_args()
    
    if not args.db:
        print("Error: Database file not specified")
        return 1
    
    exit_code = 0
    
    if args.analyze:
        exit_code = analyze_database(args.db)
    
    if args.export and exit_code == 0:
        exit_code = export_results(args.db, args.export)
    
    return exit_code

if __name__ == "__main__":
    sys.exit(main())
