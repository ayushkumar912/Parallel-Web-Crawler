#!/usr/bin/env python3
"""
Configuration management script for the Parallel Web Crawler
"""

import json
import argparse
import sys
from pathlib import Path

def create_default_config():
    """Create a default configuration file"""
    default_config = {
        "crawling": {
            "max_depth": 2,
            "crawl_delay": 1.0,
            "request_timeout": 10,
            "max_urls_per_domain": 100,
            "respect_robots_txt": True,
            "verify_ssl": False
        },
        "request_settings": {
            "user_agent": "Mozilla/5.0 (compatible; AdvancedParallelCrawler/1.0)",
            "max_redirects": 5
        },
        "storage": {
            "database_path": "crawler.db",
            "urls_file": "urls.txt"
        },
        "filters": {
            "allowed_schemes": ["http", "https"],
            "blocked_extensions": [".pdf", ".jpg", ".jpeg", ".png", ".gif", ".mp4", ".avi", ".zip", ".tar", ".gz"],
            "blocked_domains": [],
            "max_url_length": 2000
        }
    }

def save_config(config, filepath):
    """Save configuration to file"""
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        print(f"Configuration saved to {filepath}")
        return True
    except Exception as e:
        print(f"Error saving configuration: {e}")
        return False

def load_config(filepath):
    """Load configuration from file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config
    except FileNotFoundError:
        print(f"Configuration file not found: {filepath}")
        return None
    except Exception as e:
        print(f"Error loading configuration: {e}")
        return None

def validate_config(config):
    """Validate configuration settings"""
    errors = []
    
    # Check required sections
    required_sections = ['crawling', 'request_settings', 'filters', 'storage']
    for section in required_sections:
        if section not in config:
            errors.append(f"Missing required section: {section}")
    
    if 'crawling' in config:
        crawling = config['crawling']
        
        if crawling.get('max_depth', 0) < 0:
            errors.append("max_depth must be non-negative")
        
        if crawling.get('crawl_delay', 0) < 0:
            errors.append("crawl_delay must be non-negative")
        
        if crawling.get('request_timeout', 0) <= 0:
            errors.append("request_timeout must be positive")
        
        if crawling.get('max_urls_per_domain', 0) <= 0:
            errors.append("max_urls_per_domain must be positive")
    
    if 'storage' in config:
        storage = config['storage']
        
        if not storage.get('database_path'):
            errors.append("database_path cannot be empty")
        
        if not storage.get('urls_file'):
            errors.append("urls_file cannot be empty")
    
    return errors

def interactive_config():
    """Create configuration interactively"""
    print("Interactive Configuration Setup")
    print("=" * 40)
    
    config = create_config_template()
    
    # Basic crawling settings
    print("\n1. Crawling Settings:")
    
    while True:
        try:
            max_depth = input(f"Maximum crawling depth [{config['crawling']['max_depth']}]: ").strip()
            if max_depth:
                config['crawling']['max_depth'] = int(max_depth)
            break
        except ValueError:
            print("Please enter a valid number")
    
    while True:
        try:
            crawl_delay = input(f"Delay between requests (seconds) [{config['crawling']['crawl_delay']}]: ").strip()
            if crawl_delay:
                config['crawling']['crawl_delay'] = float(crawl_delay)
            break
        except ValueError:
            print("Please enter a valid number")
    
    while True:
        try:
            max_urls = input(f"Maximum URLs per domain [{config['crawling']['max_urls_per_domain']}]: ").strip()
            if max_urls:
                config['crawling']['max_urls_per_domain'] = int(max_urls)
            break
        except ValueError:
            print("Please enter a valid number")
    
    # Robots.txt compliance
    print("\n2. Compliance Settings:")
    robots_txt = input(f"Respect robots.txt? [{config['crawling']['respect_robots_txt']}] (y/n): ").strip().lower()
    if robots_txt in ['n', 'no', 'false']:
        config['crawling']['respect_robots_txt'] = False
    elif robots_txt in ['y', 'yes', 'true']:
        config['crawling']['respect_robots_txt'] = True
    
    # File paths
    print("\n3. Storage Settings:")
    db_path = input(f"Database file path [{config['storage']['database_path']}]: ").strip()
    if db_path:
        config['storage']['database_path'] = db_path
    
    urls_file = input(f"URLs file path [{config['storage']['urls_file']}]: ").strip()
    if urls_file:
        config['storage']['urls_file'] = urls_file
    
    return config

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Parallel Web Crawler Configuration Manager')
    parser.add_argument('--create', action='store_true', help='Create default configuration file')
    parser.add_argument('--interactive', action='store_true', help='Interactive configuration setup')
    parser.add_argument('--validate', metavar='FILE', help='Validate configuration file')
    parser.add_argument('--output', default='crawler_config.json', help='Output configuration file')
    
    args = parser.parse_args()
    
    if args.create:
        config = create_config_template()
        if save_config(config, args.output):
            print(f"Default configuration created: {args.output}")
            print("Edit this file to customize your crawler settings.")
        return 0
    
    elif args.interactive:
        config = interactive_config()
        if save_config(config, args.output):
            print(f"\nConfiguration saved to: {args.output}")
            print("You can now use this configuration with the crawler.")
        return 0
    
    elif args.validate:
        config = load_config(args.validate)
        if config is None:
            return 1
        
        errors = validate_config(config)
        if errors:
            print(f"Configuration validation failed:")
            for error in errors:
                print(f"  ❌ {error}")
            return 1
        else:
            print(f"✅ Configuration is valid: {args.validate}")
            return 0
    
    else:
        parser.print_help()
        return 1

if __name__ == "__main__":
    sys.exit(main())
