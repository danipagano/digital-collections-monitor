#!/usr/bin/env python3
"""
Digital Collection Uptime Monitor
Monitors the availability and performance of digital archive collections
"""

import requests
import sqlite3
import json
import time
from datetime import datetime, timedelta
import argparse
import sys
from typing import Dict, List, Tuple
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

class DigitalCollectionMonitor:
    def __init__(self, db_path: str = "collections_monitor.db"):
        self.db_path = db_path
        self.init_database()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Digital-Collection-Monitor/1.0 (Research Tool)'
        })
        
        # Digital collections to monitor
        self.collections = {
            "Library of Congress Digital Collections": "https://www.loc.gov/collections/",
            "Digital Public Library of America": "https://dp.la/",
            "Internet Archive": "https://archive.org/",
            "HathiTrust Digital Library": "https://www.hathitrust.org/",
            "Europeana": "https://www.europeana.eu/",
            "World Digital Library": "https://www.wdl.org/",
            "National Archives Catalog": "https://catalog.archives.gov/",
            "Smithsonian Open Access": "https://www.si.edu/openaccess",
            "Getty Research Institute": "https://www.getty.edu/research/",
            "DPLA - Digital Public Library of America": "https://pro.dp.la/",
            "Perseus Digital Library": "http://www.perseus.tufts.edu/",
            "Google Arts & Culture": "https://artsandculture.google.com/",
            "Metropolitan Museum API": "https://metmuseum.github.io/",
            "Biodiversity Heritage Library": "https://www.biodiversitylibrary.org/",
            "David Rumsey Map Collection": "https://www.davidrumsey.com/"
        }
    
    def init_database(self):
        """Initialize SQLite database with required tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS monitoring_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                collection_name TEXT NOT NULL,
                url TEXT NOT NULL,
                status_code INTEGER,
                response_time REAL,
                content_length INTEGER,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                error_message TEXT,
                is_accessible BOOLEAN
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                collection_name TEXT NOT NULL,
                alert_type TEXT NOT NULL,
                message TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                resolved BOOLEAN DEFAULT FALSE
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def check_collection(self, name: str, url: str, timeout: int = 10) -> Dict:
        """Check a single digital collection's availability"""
        result = {
            'collection_name': name,
            'url': url,
            'timestamp': datetime.now().isoformat(),
            'is_accessible': False,
            'status_code': None,
            'response_time': None,
            'content_length': None,
            'error_message': None
        }
        
        try:
            start_time = time.time()
            response = self.session.get(url, timeout=timeout, allow_redirects=True)
            end_time = time.time()
            
            result['status_code'] = response.status_code
            result['response_time'] = round(end_time - start_time, 2)
            result['content_length'] = len(response.content)
            result['is_accessible'] = 200 <= response.status_code < 400
            
            if not result['is_accessible']:
                result['error_message'] = f"HTTP {response.status_code}"
                
        except requests.exceptions.Timeout:
            result['error_message'] = "Request timeout"
        except requests.exceptions.ConnectionError:
            result['error_message'] = "Connection error"
        except requests.exceptions.RequestException as e:
            result['error_message'] = str(e)
        except Exception as e:
            result['error_message'] = f"Unexpected error: {str(e)}"
        
        return result
    
    def monitor_all_collections(self, max_workers: int = 5) -> List[Dict]:
        """Monitor all collections concurrently"""
        print(f"Monitoring {len(self.collections)} digital collections...")
        
        results = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_collection = {
                executor.submit(self.check_collection, name, url): (name, url) 
                for name, url in self.collections.items()
            }
            
            for future in as_completed(future_to_collection):
                name, url = future_to_collection[future]
                try:
                    result = future.result()
                    results.append(result)
                    
                    # Print real-time status
                    status = "✅ UP" if result['is_accessible'] else "❌ DOWN"
                    response_time = f"({result['response_time']}s)" if result['response_time'] else ""
                    print(f"{status} {name} {response_time}")
                    
                except Exception as e:
                    print(f"❌ {name}: Error - {str(e)}")
        
        return results
    
    def save_results(self, results: List[Dict]):
        """Save monitoring results to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for result in results:
            cursor.execute('''
                INSERT INTO monitoring_results 
                (collection_name, url, status_code, response_time, content_length, 
                 timestamp, error_message, is_accessible)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                result['collection_name'],
                result['url'],
                result['status_code'],
                result['response_time'],
                result['content_length'],
                result['timestamp'],
                result['error_message'],
                result['is_accessible']
            ))
        
        conn.commit()
        conn.close()
    
    def get_current_status(self) -> List[Dict]:
        """Get the most recent status for all collections"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT collection_name, url, status_code, response_time, 
                   timestamp, error_message, is_accessible
            FROM monitoring_results
            WHERE timestamp IN (
                SELECT MAX(timestamp)
                FROM monitoring_results
                GROUP BY collection_name
            )
            ORDER BY collection_name
        ''')
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'collection_name': row[0],
                'url': row[1],
                'status_code': row[2],
                'response_time': row[3],
                'timestamp': row[4],
                'error_message': row[5],
                'is_accessible': bool(row[6])
            })
        
        conn.close()
        return results
    
    def get_uptime_stats(self, hours: int = 24) -> Dict:
        """Calculate uptime statistics for the specified time period"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        since_time = (datetime.now() - timedelta(hours=hours)).isoformat()
        
        cursor.execute('''
            SELECT collection_name,
                   COUNT(*) as total_checks,
                   SUM(CASE WHEN is_accessible THEN 1 ELSE 0 END) as successful_checks,
                   AVG(response_time) as avg_response_time
            FROM monitoring_results
            WHERE timestamp > ?
            GROUP BY collection_name
            ORDER BY collection_name
        ''', (since_time,))
        
        stats = {}
        for row in cursor.fetchall():
            collection_name, total, successful, avg_time = row
            uptime_percent = (successful / total * 100) if total > 0 else 0
            stats[collection_name] = {
                'uptime_percent': round(uptime_percent, 2),
                'total_checks': total,
                'successful_checks': successful,
                'avg_response_time': round(avg_time, 2) if avg_time else None
            }
        
        conn.close()
        return stats
    
    def display_status_report(self):
        """Display a formatted status report"""
        current_status = self.get_current_status()
        uptime_stats = self.get_uptime_stats(24)
        
        print("\n" + "="*80)
        print("DIGITAL COLLECTIONS STATUS REPORT")
        print("="*80)
        print(f"Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Monitoring {len(current_status)} digital collections\n")
        
        # Current status
        up_count = sum(1 for result in current_status if result['is_accessible'])
        down_count = len(current_status) - up_count
        
        print(f"Current Status: {up_count} UP, {down_count} DOWN")
        print("-" * 40)
        
        for result in current_status:
            status_icon = "✅" if result['is_accessible'] else "❌"
            response_time = f" ({result['response_time']}s)" if result['response_time'] else ""
            error_msg = f" - {result['error_message']}" if result['error_message'] else ""
            
            print(f"{status_icon} {result['collection_name']}{response_time}{error_msg}")
        
        # 24-hour uptime statistics
        if uptime_stats:
            print(f"\n24-Hour Uptime Statistics:")
            print("-" * 40)
            
            for collection, stats in uptime_stats.items():
                uptime = stats['uptime_percent']
                checks = stats['total_checks']
                avg_time = stats['avg_response_time']
                
                uptime_status = "🟢" if uptime >= 99 else "🟡" if uptime >= 95 else "🔴"
                avg_time_str = f" (avg: {avg_time}s)" if avg_time else ""
                
                print(f"{uptime_status} {collection}: {uptime}% uptime ({checks} checks){avg_time_str}")
    
    def run_monitoring_cycle(self):
        """Run a complete monitoring cycle"""
        print(f"Starting monitoring cycle at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        results = self.monitor_all_collections()
        self.save_results(results)
        
        print(f"\nMonitoring cycle completed. Results saved to {self.db_path}")
        
        # Show summary
        accessible_count = sum(1 for r in results if r['is_accessible'])
        total_count = len(results)
        
        print(f"Summary: {accessible_count}/{total_count} collections accessible")
        
        return results

def main():
    parser = argparse.ArgumentParser(description='Digital Collection Uptime Monitor')
    parser.add_argument('--check', action='store_true', 
                       help='Run a monitoring check')
    parser.add_argument('--status', action='store_true',
                       help='Show current status report')
    parser.add_argument('--db', default='collections_monitor.db',
                       help='Database file path')
    
    args = parser.parse_args()
    
    monitor = DigitalCollectionMonitor(db_path=args.db)
    
    if args.check:
        monitor.run_monitoring_cycle()
    elif args.status:
        monitor.display_status_report()
    else:
        print("Digital Collection Uptime Monitor")
        print("Usage:")
        print("  python monitor.py --check    # Run monitoring check")
        print("  python monitor.py --status   # Show status report")
        print("\nFor help: python monitor.py --help")

if __name__ == "__main__":
    main()