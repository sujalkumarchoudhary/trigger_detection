"""
Real-Time Trigger Detection System - CLI Entry Point
"""
import argparse
import logging
import sys
import os
import json
from datetime import datetime

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)
logger = logging.getLogger(__name__)


def setup_monitors():
    """Initialize all monitors"""
    from monitors import NewsMonitor, RegulatoryMonitor, TenderMonitor, FinancialMonitor
    
    return {
        'news_monitor': NewsMonitor(),
        'regulatory_monitor': RegulatoryMonitor(),
        'tender_monitor': TenderMonitor(),
        'financial_monitor': FinancialMonitor(),
    }


def run_all_monitors(monitors, db=None):
    """Run all monitors and store results"""
    from database import TriggerDatabase
    
    if db is None:
        db = TriggerDatabase()
    
    all_results = []
    
    for name, monitor in monitors.items():
        print(f"\n{'='*60}")
        print(f"Running {name}...")
        print('='*60)
        
        try:
            results = monitor.run()
            all_results.extend(results)
            
            print(f"✓ Found {len(results)} triggers")
            
            # Store in database
            for result in results:
                from database.models import TriggerEvent
                trigger = TriggerEvent(
                    source_type=result.source_type,
                    source_name=result.source_name,
                    title=result.title,
                    content=result.content,
                    url=result.url,
                    company_name=result.company_name,
                    trigger_keywords=json.dumps(result.trigger_keywords),
                    sentiment_score=result.sentiment_score,
                    trigger_score=result.trigger_score,
                    detected_at=result.detected_at,
                    published_at=result.published_at,
                )
                db.insert_trigger(trigger)
                
        except Exception as e:
            logger.error(f"Failed to run {name}: {e}")
    
    return all_results


def run_single_monitor(monitor_name: str) -> list:
    """Run a specific monitor"""
    monitors = setup_monitors()
    
    if monitor_name not in monitors:
        print(f"Unknown monitor: {monitor_name}")
        print(f"Available: {list(monitors.keys())}")
        return []
    
    from database import TriggerDatabase
    db = TriggerDatabase()
    
    monitor = monitors[monitor_name]
    results = monitor.run()
    
    # Store results
    for result in results:
        from database.models import TriggerEvent
        trigger = TriggerEvent(
            source_type=result.source_type,
            source_name=result.source_name,
            title=result.title,
            content=result.content,
            url=result.url,
            company_name=result.company_name,
            trigger_keywords=json.dumps(result.trigger_keywords),
            sentiment_score=result.sentiment_score,
            trigger_score=result.trigger_score,
            detected_at=result.detected_at,
            published_at=result.published_at,
        )
        db.insert_trigger(trigger)
    
    return results


def start_scheduler():
    """Start the automated scheduler"""
    from scheduler import TriggerScheduler
    from database import TriggerDatabase
    
    print("\n" + "="*60)
    print("Starting Trigger Detection Scheduler")
    print("="*60)
    
    monitors = setup_monitors()
    db = TriggerDatabase()
    
    scheduler = TriggerScheduler()
    
    # Add jobs with configured intervals
    from config.trigger_config import SCHEDULE_CONFIG
    
    for monitor_name, config in SCHEDULE_CONFIG.items():
        if monitor_name in monitors:
            def make_job_func(monitor, database):
                def job():
                    results = monitor.run()
                    for result in results:
                        from database.models import TriggerEvent
                        trigger = TriggerEvent(
                            source_type=result.source_type,
                            source_name=result.source_name,
                            title=result.title,
                            content=result.content,
                            url=result.url,
                            company_name=result.company_name,
                            trigger_keywords=json.dumps(result.trigger_keywords),
                            sentiment_score=result.sentiment_score,
                            trigger_score=result.trigger_score,
                            detected_at=result.detected_at,
                            published_at=result.published_at,
                        )
                        database.insert_trigger(trigger)
                    return results
                return job
            
            scheduler.add_job(
                job_id=monitor_name,
                func=make_job_func(monitors[monitor_name], db),
                interval_hours=config['interval_hours'],
                enabled=config['enabled'],
            )
            print(f"  ✓ Scheduled {monitor_name} (every {config['interval_hours']}h)")
    
    scheduler.start()
    
    print("\nScheduler running. Press Ctrl+C to stop.")
    
    try:
        while True:
            import time
            time.sleep(60)  # Keep alive
    except KeyboardInterrupt:
        print("\nStopping scheduler...")
        scheduler.stop()
        print("Done.")


def show_stats():
    """Show trigger statistics"""
    from database import TriggerDatabase
    
    db = TriggerDatabase()
    stats = db.get_trigger_stats()
    
    print("\n" + "="*60)
    print("TRIGGER DETECTION STATISTICS")
    print("="*60)
    
    print(f"\n📊 Total Triggers: {stats['total_triggers']}")
    print(f"🔥 High Score (≥7): {stats['high_score_count']}")
    print(f"🕐 Last 24h: {stats['recent_triggers']}")
    
    print("\n📁 By Source:")
    for source, count in stats.get('by_source', {}).items():
        print(f"   {source}: {count}")
    
    print("\n🏢 Top Companies:")
    for company, count in list(stats.get('top_companies', {}).items())[:5]:
        print(f"   {company}: {count}")


def export_triggers(filepath: str):
    """Export triggers to CSV"""
    from database import TriggerDatabase
    
    db = TriggerDatabase()
    count = db.export_to_csv(filepath)
    print(f"\n✓ Exported {count} triggers to {filepath}")


def test_mode():
    """Quick test mode - run each monitor briefly"""
    print("\n" + "="*60)
    print("TEST MODE - Running quick trigger detection test")
    print("="*60)
    
    monitors = setup_monitors()
    
    for name, monitor in monitors.items():
        print(f"\n🔍 Testing {name}...")
        
        try:
            results = monitor.run()
            print(f"   ✓ Success! Found {len(results)} triggers")
            
            # Show top result
            if results:
                top = results[0]
                print(f"   📌 Top: {top.title[:60]}... (score: {top.trigger_score})")
                
        except Exception as e:
            print(f"   ✗ Error: {e}")
    
    print("\n" + "="*60)
    print("Test complete!")


def main():
    parser = argparse.ArgumentParser(
        description="Real-Time Trigger Detection System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                    Run all monitors once
  python main.py --monitor news     Run only news monitor
  python main.py --schedule         Start automated scheduler
  python main.py --stats            Show trigger statistics
  python main.py --export out.csv   Export triggers to CSV
  python main.py --test-mode        Quick test of all monitors
        """
    )
    
    parser.add_argument(
        '--monitor', '-m',
        choices=['news', 'regulatory', 'tender', 'financial'],
        help='Run specific monitor only'
    )
    parser.add_argument(
        '--schedule', '-s',
        action='store_true',
        help='Start automated scheduler'
    )
    parser.add_argument(
        '--stats',
        action='store_true',
        help='Show trigger statistics'
    )
    parser.add_argument(
        '--export', '-e',
        metavar='FILE',
        help='Export triggers to CSV file'
    )
    parser.add_argument(
        '--test-mode', '-t',
        action='store_true',
        help='Run quick test mode'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    print("\n🔔 Real-Time Trigger Detection System")
    print(f"   Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        if args.test_mode:
            test_mode()
        elif args.schedule:
            start_scheduler()
        elif args.stats:
            show_stats()
        elif args.export:
            export_triggers(args.export)
        elif args.monitor:
            monitor_map = {
                'news': 'news_monitor',
                'regulatory': 'regulatory_monitor',
                'tender': 'tender_monitor',
                'financial': 'financial_monitor',
            }
            results = run_single_monitor(monitor_map[args.monitor])
            print(f"\n✓ Found {len(results)} triggers from {args.monitor} monitor")
        else:
            # Default: run all monitors
            monitors = setup_monitors()
            results = run_all_monitors(monitors)
            
            print("\n" + "="*60)
            print("SUMMARY")
            print("="*60)
            print(f"Total triggers detected: {len(results)}")
            
            # Show top 5
            if results:
                print("\nTop 5 Triggers:")
                for i, r in enumerate(sorted(results, key=lambda x: x.trigger_score, reverse=True)[:5], 1):
                    print(f"  {i}. [{r.trigger_score:.1f}] {r.title[:50]}...")
            
    except KeyboardInterrupt:
        print("\n\nInterrupted by user.")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
