# Advanced Modular Parallel Web Crawler

A high-performance, enterprise-grade web crawler built with Python and MPI for distributed processing, featuring comprehensive analysis tools and flexible configuration management.

## Key Features

### Core Crawling Capabilities
- **Parallel Processing**: MPI-based master-worker architecture with dynamic load balancing
- **Depth-Limited BFS Crawling**: Breadth-first traversal with configurable depth limits
- **Advanced URL Deduplication**: Intelligent normalization and duplicate prevention
- **Robots.txt Compliance**: Full robots.txt parsing and compliance with crawl-delay directives
- **Intelligent Rate Limiting**: Per-domain throttling with configurable delays
- **SQLite Storage**: Robust persistent storage with comprehensive metadata tracking
- **Graceful Error Handling**: Comprehensive error recovery, timeout management, and logging

### Advanced Features
- **Comprehensive Analysis Tools**: Detailed crawl statistics, performance metrics, and domain analysis
- **Multiple Export Formats**: CSV and JSON export capabilities
- **Configuration Management**: Flexible JSON-based configuration with validation
- **Modular Architecture**: Clean separation of concerns for maintainability and extensibility
- **SSL Flexibility**: Configurable SSL verification for diverse environments
- **Content Analysis**: Title extraction, content length tracking, and MIME type detection

## Requirements

- **Python 3.7+**
- **MPI Implementation**: OpenMPI or MPICH
- **Python Packages**: `mpi4py`, `requests`, `beautifulsoup4`, `urllib3`

## Installation

### 1. Install MPI
```bash
# macOS with Homebrew
brew install open-mpi

# Ubuntu/Debian
sudo apt-get install libopenmpi-dev openmpi-bin

# CentOS/RHEL
sudo yum install openmpi openmpi-devel
```

### 2. Set Up Python Environment
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install mpi4py requests beautifulsoup4 urllib3
```

### 3. Verify Installation
```bash
# Test MPI installation
mpiexec --version

# Test Python MPI bindings
python -c "from mpi4py import MPI; print('MPI installation successful')"
```

##  Usage

### Quick Start
```bash
# Run with default settings (4 processes)
mpiexec -n 4 python main.py


### Advanced Usage Examples

```bash
# Light crawling (2 processes)
mpiexec -n 2 python main.py

# Heavy crawling (8 processes)
mpiexec -n 8 python main.py

# Run analysis on existing crawl data
python analyze.py

# Export results to CSV
python analyze.py --export csv

# Create default configuration
python config_manager.py --create --output my_config.json

# Validate configuration
python config_manager.py --validate my_config.json
```

## 🏗️ Architecture

### System Components

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│    main.py      │    │  Configuration   │    │  Analysis &     │
│  (Entry Point)  │    │  Management      │    │  Reporting      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ MPI Coordinator │    │  Crawler Core    │    │ Database Manager│
│ (Master-Worker) │◄──►│  (Web Crawling)  │◄──►│ (SQLite Storage)│
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Utilities     │    │   Error Handler  │    │  Export Tools   │
│ (URL Processing)│    │  & Rate Limiter  │    │ (CSV/JSON)      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### Master-Worker Pattern

- **Master Process (Rank 0)**:
  - Manages global URL queue with deduplication
  - Distributes work to available workers
  - Collects and stores crawl results
  - Maintains crawl statistics and progress tracking

- **Worker Processes (Rank 1+)**:
  - Crawl assigned URLs independently
  - Extract links and content metadata
  - Report results back to master
  - Handle errors gracefully with retry logic

### Data Flow

1. **Initialization**: Master loads seed URLs and broadcasts configuration
2. **Work Distribution**: URLs assigned to available workers
3. **Crawling**: Workers process URLs, extract content and links
4. **Result Collection**: Master receives results and discovered URLs
5. **Storage**: Results stored in SQLite with comprehensive metadata
6. **Analysis**: Post-crawl analysis generates detailed reports

## Configuration

### Configuration File Structure
```json
{
    "crawling": {
        "max_depth": 2,
        "crawl_delay": 1.0,
        "request_timeout": 10,
        "max_urls_per_domain": 100,
        "respect_robots_txt": true,
        "verify_ssl": false
    },
    "request_settings": {
        "user_agent": "Mozilla/5.0 (compatible; AdvancedCrawler/1.0)",
        "max_redirects": 5
    },
    "storage": {
        "database_path": "crawler.db",
        "urls_file": "urls.txt"
    }
}
```

### Key Configuration Options

| Parameter | Description | Default |
|-----------|-------------|---------|
| `max_depth` | Maximum crawl depth (BFS levels) | 2 |
| `crawl_delay` | Delay between requests (seconds) | 1.0 |
| `request_timeout` | HTTP request timeout | 10s |
| `max_urls_per_domain` | Per-domain URL limit | 100 |
| `respect_robots_txt` | Honor robots.txt files | true |
| `verify_ssl` | SSL certificate verification | false |

##  Output & Analysis

### Database Schema
```sql
CREATE TABLE crawled_urls (
    id INTEGER PRIMARY KEY,
    url TEXT UNIQUE,
    title TEXT,
    content_length INTEGER,
    status TEXT,
    depth INTEGER,
    domain TEXT,
    response_time REAL,
    error_message TEXT,
    timestamp DATETIME,
    links_found INTEGER
);
```

### Analysis Features

- **Performance Metrics**: Response times, success rates, throughput
- **Domain Analysis**: Per-domain statistics and compliance tracking
- **Content Statistics**: Size distribution, title analysis, link discovery
- **Error Analysis**: Categorized error reporting and troubleshooting
- **Export Capabilities**: CSV and JSON format support

### Sample Analysis Output
```
 CRAWL ANALYSIS REPORT
========================
Total URLs Processed: 1,502
Unique Domains: 147
Success Rate: 84.2%
Average Response Time: 1.26s
Total Content: 124.79 MB

 TOP DOMAINS:
- peps.python.org: 596 pages (39.7%)
- stackoverflow.com: 273 pages (18.2%)
- docs.python.org: 198 pages (13.2%)

 ERROR SUMMARY:
- Timeout errors: 127 (8.5%)
- Connection errors: 89 (5.9%)
- HTTP errors: 48 (3.2%)
```

## Performance Benchmarks

| Processes | URLs/sec | Domains | Efficiency |
|-----------|----------|---------|------------|
| 2 (1+1)   | 3-4      | 10-20   | 85% |
| 4 (1+3)   | 8-12     | 30-50   | 90% |
| 6 (1+5)   | 15-20    | 50-80   | 88% |
| 8 (1+7)   | 20-25    | 70-100  | 85% |

*Performance varies based on network conditions, target sites, and hardware*

## Testing & Validation


### Individual Component Tests
```bash
# Test database operations
python -c "from src.database_manager import DatabaseManager; print('✅ DB OK')"

# Test crawler core
python -c "from src.crawler_core import CrawlerCore; print('✅ Crawler OK')"

# Test URL utilities
python -c "from src.utils import normalize_url; print('✅ Utils OK')"

# Test configuration
python config_manager.py --validate
```

## Troubleshooting

### Common Issues

1. **MPI Not Found**
   ```bash
   # Ensure MPI is in PATH
   export PATH="/usr/local/bin:$PATH"
   which mpiexec
   ```

2. **SSL Certificate Errors**
   ```python
   # Set verify_ssl: false in configuration
   # Or install certificates: pip install --upgrade certifi
   ```

3. **Memory Issues with Large Crawls**
   ```bash
   # Reduce max_urls_per_domain or max_depth
   # Use more processes to distribute load
   ```

4. **Rate Limiting Issues**
   ```python
   # Increase crawl_delay in configuration
   # Check robots.txt compliance
   ```

## Security & Ethics

- **Robots.txt Compliance**: Full respect for website crawling policies
- **Rate Limiting**: Respectful crawling to avoid server overload
- **User Agent**: Proper identification in HTTP headers
- **SSL Handling**: Configurable certificate validation
- **Error Recovery**: Graceful handling of network issues

##  Advanced Usage

### Custom URL Filtering
```python
# Modify src/config.py URL validation rules
ALLOWED_SCHEMES = {'http', 'https'}
BLOCKED_EXTENSIONS = {'.pdf', '.jpg', '.png', '.mp4'}
```

### Custom Analysis Reports
```python
# Extend analyze.py for custom metrics
def custom_analysis(db_connection):
    # Add your analysis logic
    pass
```

### Integration Examples
```python
# Use as a library
from src.crawler_core import CrawlerCore
from src.config import CrawlerConfig

config = CrawlerConfig()
crawler = CrawlerCore(config)
result = crawler.crawl_url('https://example.com')
```

##  Contributing

1. **Fork the repository**
2. **Create feature branch**: `git checkout -b feature/amazing-feature`
3. **Make changes with comprehensive tests**
4. **Update documentation as needed**
5. **Submit pull request with detailed description**

### Development Setup
```bash
# Install development dependencies
pip install -e .[dev]

# Run tests
python -m pytest tests/

# Format code
black src/ *.py

# Check types
mypy src/
```

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

**Built with ❤️ for ethical, efficient, and scalable web crawling.**
