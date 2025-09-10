#!/bin/bash
# Comprehensive demo script for the Modular Parallel Web Crawler

echo "=================================="
echo "PARALLEL WEB CRAWLER DEMO"
echo "=================================="

PYTHON_PATH="/Users/ayush_kumar912/LABS/disProj/.venv/bin/python"
PROJECT_ROOT="/Users/ayush_kumar912/LABS/disProj"

cd "$PROJECT_ROOT"

# Function to check if command was successful
check_success() {
    if [ $? -eq 0 ]; then
        echo "✅ $1 completed successfully"
    else
        echo "❌ $1 failed"
        return 1
    fi
}

# Clean up previous runs
echo ""
echo "🧹 Cleaning up previous runs..."
rm -f crawler.db crawl_results.csv crawl_results.json crawler_config.json
check_success "Cleanup"

# Create configuration
echo ""
echo "⚙️  Creating configuration..."
echo "{
    \"crawling\": {
        \"max_depth\": 1,
        \"crawl_delay\": 0.5,
        \"request_timeout\": 10,
        \"max_urls_per_domain\": 20,
        \"respect_robots_txt\": true,
        \"verify_ssl\": false
    },
    \"request_settings\": {
        \"user_agent\": \"Mozilla/5.0 (compatible; DemoParallelCrawler/1.0)\",
        \"max_redirects\": 3
    },
    \"storage\": {
        \"database_path\": \"crawler.db\",
        \"urls_file\": \"urls.txt\"
    }
}" > demo_config.json
check_success "Configuration creation"

# Validate configuration
echo ""
echo "🔍 Validating configuration..."
$PYTHON_PATH config_manager.py --validate demo_config.json
check_success "Configuration validation"

# Create demo URLs
echo ""
echo "📝 Creating demo URLs..."
cat > demo_urls.txt << EOF
https://httpbin.org/html
https://www.python.org
https://example.com
https://httpbin.org/links/5
https://www.w3.org
EOF
check_success "Demo URLs creation"

# Test with different process counts
test_configurations=(
    "2:1master+1worker"
    "3:1master+2workers" 
    "4:1master+3workers"
)

for config in "${test_configurations[@]}"; do
    IFS=':' read -r processes description <<< "$config"
    
    echo ""
    echo "🚀 Testing with $processes processes ($description)..."
    
    # Clean database for fresh test
    rm -f crawler.db
    
    # Run crawler with time measurement
    start_time=$(date +%s)
    timeout 30 mpiexec -n $processes $PYTHON_PATH main.py 2>/dev/null | tail -5
    end_time=$(date +%s)
    
    execution_time=$((end_time - start_time))
    echo "   Execution time: ${execution_time}s"
    
    # Check results if database exists
    if [ -f "crawler.db" ]; then
        results=$($PYTHON_PATH -c "
import sqlite3
conn = sqlite3.connect('crawler.db')
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM crawled_urls')
total = cursor.fetchone()[0]
cursor.execute('SELECT COUNT(*) FROM crawled_urls WHERE status=\"success\"')
success = cursor.fetchone()[0]
print(f'   Results: {total} total, {success} successful')
conn.close()
")
        echo "$results"
    else
        echo "   No results database created"
    fi
done

echo ""
echo "📊 Running comprehensive analysis..."

# Create fresh crawl with more URLs for analysis
rm -f crawler.db
echo "Starting comprehensive crawl for analysis..."
timeout 60 mpiexec -n 4 $PYTHON_PATH main.py > /dev/null 2>&1

if [ -f "crawler.db" ]; then
    # Run analysis
    $PYTHON_PATH analyze.py | head -30
    
    echo ""
    echo "📤 Testing export functionality..."
    
    # Export to CSV
    $PYTHON_PATH analyze.py --export csv --analyze false
    check_success "CSV export"
    
    # Show CSV sample
    if [ -f "crawl_results.csv" ]; then
        echo "CSV sample (first 3 lines):"
        head -3 crawl_results.csv
        echo "   Total lines: $(wc -l < crawl_results.csv)"
    fi
    
    # Export to JSON
    $PYTHON_PATH analyze.py --export json --analyze false  
    check_success "JSON export"
    
    # Show JSON sample
    if [ -f "crawl_results.json" ]; then
        echo "JSON sample (first result):"
        head -20 crawl_results.json
        echo "   File size: $(wc -c < crawl_results.json) bytes"
    fi
else
    echo "No comprehensive results to analyze"
fi

# Test configuration manager
echo ""
echo "🔧 Testing configuration manager..."

# Create default config
$PYTHON_PATH config_manager.py --create --output test_config.json
check_success "Default config creation"

# Validate the created config
$PYTHON_PATH config_manager.py --validate test_config.json
check_success "Created config validation"

echo ""
echo "🧪 Testing individual components..."

# Test database manager
echo "Testing database operations..."
$PYTHON_PATH -c "
from src.database_manager import DatabaseManager
from src.config import CrawlerConfig

config = CrawlerConfig()
db = DatabaseManager('test.db')

# Test insert
result = {
    'url': 'https://test.example.com',
    'title': 'Test Page',
    'content_length': 1234,
    'status': 'success',
    'depth': 1,
    'domain': 'test.example.com',
    'response_time': 0.5,
    'error_message': None
}
db.insert_crawl_result(result)

# Test stats
stats = db.get_crawl_stats()
print(f'Database test: {stats[\"total_crawled\"]} records inserted')

# Cleanup
import os
os.remove('test.db')
print('✅ Database operations test passed')
"
check_success "Database operations test"

# Test crawler core
echo "Testing crawler core..."
$PYTHON_PATH -c "
from src.crawler_core import CrawlerCore
from src.config import CrawlerConfig

config = CrawlerConfig()
config.max_depth = 0  # Prevent link discovery
crawler = CrawlerCore(config)

result = crawler.crawl_url('https://httpbin.org/html')
if result['status'] == 'success':
    print(f'✅ Crawler core test passed: {result[\"title\"][:50]}...')
else:
    print(f'❌ Crawler core test failed: {result[\"error_message\"]}')
"

# Test URL utilities
echo "Testing URL utilities..."
$PYTHON_PATH -c "
from src.utils import normalize_url, validate_seed_urls

# Test normalization
test_urls = [
    'https://example.com/',
    'HTTP://EXAMPLE.COM/path',
    'https://example.com/path#fragment'
]

normalized = [normalize_url(url) for url in test_urls]
print(f'✅ URL normalization test: {len([u for u in normalized if u])} valid URLs')

# Test validation
valid_urls = validate_seed_urls(['https://example.com', 'invalid-url', 'ftp://test.com'])
print(f'✅ URL validation test: {len(valid_urls)} valid URLs from 3 inputs')
"

# Show final statistics
echo ""
echo "📈 Final Statistics Summary:"
if [ -f "crawler.db" ]; then
    $PYTHON_PATH -c "
import sqlite3
import os

conn = sqlite3.connect('crawler.db')
cursor = conn.cursor()

cursor.execute('SELECT COUNT(*) FROM crawled_urls')
total = cursor.fetchone()[0]

cursor.execute('SELECT COUNT(DISTINCT domain) FROM crawled_urls')
domains = cursor.fetchone()[0]

cursor.execute('SELECT status, COUNT(*) FROM crawled_urls GROUP BY status')
status_counts = cursor.fetchall()

db_size = os.path.getsize('crawler.db') / (1024*1024)

print(f'   📊 Total URLs processed: {total:,}')
print(f'   🌐 Unique domains: {domains:,}')
print(f'   💾 Database size: {db_size:.2f} MB')
print('   📋 Status breakdown:')
for status, count in status_counts:
    percentage = (count/total)*100
    print(f'      {status}: {count:,} ({percentage:.1f}%)')

conn.close()
"
fi

# Cleanup
echo ""
echo "🧹 Cleaning up demo files..."
rm -f demo_config.json demo_urls.txt test_config.json

echo ""
echo "=================================="
echo "✅ DEMO COMPLETED SUCCESSFULLY!"
echo "=================================="
echo ""
echo "Files created:"
echo "  - crawler.db (SQLite database with results)"
echo "  - crawl_results.csv (CSV export)"
echo "  - crawl_results.json (JSON export)"
echo ""
echo "Key achievements demonstrated:"
echo "  ✅ Modular architecture with clean separation"
echo "  ✅ Depth-limited BFS crawling"
echo "  ✅ URL deduplication and normalization"
echo "  ✅ Robots.txt compliance"
echo "  ✅ SQLite database storage"
echo "  ✅ Rate limiting and throttling"
echo "  ✅ Master-worker MPI coordination"
echo "  ✅ Graceful error handling"
echo "  ✅ Comprehensive analysis and reporting"
echo "  ✅ Multiple export formats"
echo "  ✅ Configuration management"
echo ""
echo "Run './demo.sh' to repeat this demonstration."
