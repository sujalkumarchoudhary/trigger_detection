"""
Job Scheduler for automated trigger detection
"""
import logging
from datetime import datetime
from typing import Dict, List, Callable, Optional
import threading
import time

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.interval import IntervalTrigger
    APSCHEDULER_AVAILABLE = True
except ImportError:
    APSCHEDULER_AVAILABLE = False

from ..config.trigger_config import SCHEDULE_CONFIG

logger = logging.getLogger(__name__)


class TriggerScheduler:
    """
    Scheduler for automated trigger detection jobs
    Uses APScheduler if available, otherwise provides basic threading-based scheduling
    """
    
    def __init__(self):
        """Initialize scheduler"""
        self.jobs: Dict[str, dict] = {}
        self.is_running = False
        
        if APSCHEDULER_AVAILABLE:
            self.scheduler = BackgroundScheduler()
            self.use_apscheduler = True
            logger.info("Using APScheduler for job scheduling")
        else:
            self.scheduler = None
            self.use_apscheduler = False
            self._threads: Dict[str, threading.Thread] = {}
            self._stop_events: Dict[str, threading.Event] = {}
            logger.warning("APScheduler not available - using basic threading scheduler")
    
    def add_job(
        self,
        job_id: str,
        func: Callable,
        interval_hours: float = 1,
        enabled: bool = True,
        run_immediately: bool = False,
    ):
        """
        Add a scheduled job
        
        Args:
            job_id: Unique identifier for the job
            func: Function to execute
            interval_hours: Hours between executions
            enabled: Whether job is enabled
            run_immediately: Whether to run once immediately
        """
        self.jobs[job_id] = {
            'func': func,
            'interval_hours': interval_hours,
            'enabled': enabled,
            'last_run': None,
            'run_count': 0,
        }
        
        if not enabled:
            logger.info(f"Job {job_id} added but disabled")
            return
        
        if self.use_apscheduler:
            self.scheduler.add_job(
                func=self._wrap_job(job_id, func),
                trigger=IntervalTrigger(hours=interval_hours),
                id=job_id,
                replace_existing=True,
            )
            logger.info(f"Added APScheduler job: {job_id} (every {interval_hours}h)")
        else:
            # Will be started when scheduler starts
            logger.info(f"Registered job: {job_id} (every {interval_hours}h)")
        
        if run_immediately:
            self._run_job(job_id)
    
    def _wrap_job(self, job_id: str, func: Callable) -> Callable:
        """Wrap job function with logging and tracking"""
        def wrapped():
            logger.info(f"Starting job: {job_id}")
            start_time = datetime.now()
            
            try:
                result = func()
                self.jobs[job_id]['last_run'] = datetime.now()
                self.jobs[job_id]['run_count'] += 1
                
                duration = (datetime.now() - start_time).total_seconds()
                logger.info(f"Completed job: {job_id} in {duration:.1f}s")
                
                return result
                
            except Exception as e:
                logger.error(f"Job {job_id} failed: {e}", exc_info=True)
                raise
        
        return wrapped
    
    def _run_job(self, job_id: str):
        """Run a job immediately"""
        if job_id not in self.jobs:
            logger.error(f"Job not found: {job_id}")
            return
        
        job = self.jobs[job_id]
        wrapped = self._wrap_job(job_id, job['func'])
        
        # Run in thread to not block
        thread = threading.Thread(target=wrapped, daemon=True)
        thread.start()
    
    def _basic_scheduler_loop(self, job_id: str):
        """Basic scheduler loop for non-APScheduler mode"""
        job = self.jobs[job_id]
        stop_event = self._stop_events[job_id]
        interval_seconds = job['interval_hours'] * 3600
        
        while not stop_event.is_set():
            try:
                wrapped = self._wrap_job(job_id, job['func'])
                wrapped()
            except Exception as e:
                logger.error(f"Error in job {job_id}: {e}")
            
            # Wait for interval or stop
            stop_event.wait(interval_seconds)
    
    def start(self):
        """Start the scheduler"""
        if self.is_running:
            logger.warning("Scheduler already running")
            return
        
        logger.info("Starting trigger scheduler")
        
        if self.use_apscheduler:
            self.scheduler.start()
        else:
            # Start threads for each enabled job
            for job_id, job in self.jobs.items():
                if job['enabled']:
                    self._stop_events[job_id] = threading.Event()
                    thread = threading.Thread(
                        target=self._basic_scheduler_loop,
                        args=(job_id,),
                        daemon=True,
                    )
                    self._threads[job_id] = thread
                    thread.start()
                    logger.info(f"Started thread for job: {job_id}")
        
        self.is_running = True
        logger.info("Scheduler started")
    
    def stop(self):
        """Stop the scheduler"""
        if not self.is_running:
            return
        
        logger.info("Stopping trigger scheduler")
        
        if self.use_apscheduler:
            self.scheduler.shutdown(wait=False)
        else:
            # Signal all threads to stop
            for stop_event in self._stop_events.values():
                stop_event.set()
        
        self.is_running = False
        logger.info("Scheduler stopped")
    
    def get_job_status(self, job_id: str = None) -> Dict:
        """Get status of jobs"""
        if job_id:
            if job_id not in self.jobs:
                return None
            job = self.jobs[job_id]
            return {
                'job_id': job_id,
                'enabled': job['enabled'],
                'interval_hours': job['interval_hours'],
                'last_run': job['last_run'].isoformat() if job['last_run'] else None,
                'run_count': job['run_count'],
            }
        
        return {
            job_id: self.get_job_status(job_id)
            for job_id in self.jobs
        }
    
    def run_now(self, job_id: str):
        """Manually trigger a job to run now"""
        self._run_job(job_id)
    
    def enable_job(self, job_id: str):
        """Enable a disabled job"""
        if job_id in self.jobs:
            self.jobs[job_id]['enabled'] = True
            logger.info(f"Enabled job: {job_id}")
    
    def disable_job(self, job_id: str):
        """Disable a job"""
        if job_id in self.jobs:
            self.jobs[job_id]['enabled'] = False
            if self.use_apscheduler and self.scheduler.get_job(job_id):
                self.scheduler.pause_job(job_id)
            logger.info(f"Disabled job: {job_id}")


def create_default_scheduler(monitors: Dict = None) -> TriggerScheduler:
    """
    Create scheduler with default job configuration
    
    Args:
        monitors: Dict of monitor name -> monitor instance
        
    Returns:
        Configured TriggerScheduler
    """
    scheduler = TriggerScheduler()
    
    if not monitors:
        return scheduler
    
    # Add jobs based on config
    for monitor_name, config in SCHEDULE_CONFIG.items():
        if monitor_name in monitors:
            scheduler.add_job(
                job_id=monitor_name,
                func=monitors[monitor_name].run,
                interval_hours=config['interval_hours'],
                enabled=config['enabled'],
            )
    
    return scheduler
