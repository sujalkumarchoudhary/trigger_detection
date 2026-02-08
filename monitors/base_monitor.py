"""
Base Monitor class for all trigger detection monitors
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


@dataclass
class TriggerResult:
    """Result from a trigger detection scan"""
    source_type: str  # news, regulatory, tender, financial
    source_name: str  # Specific source (e.g., "PharmaBiz RSS")
    title: str
    content: str
    url: str
    company_name: Optional[str]
    trigger_keywords: List[str]
    sentiment_score: float
    trigger_score: float
    detected_at: datetime
    published_at: Optional[datetime]
    raw_data: Dict[str, Any]


class BaseMonitor(ABC):
    """
    Abstract base class for all trigger monitors
    
    All monitors should inherit from this class and implement:
    - fetch(): Get raw data from source
    - parse(): Parse raw data into structured format
    - analyze(): Analyze data for triggers
    - run(): Execute full monitoring cycle
    """
    
    def __init__(self, name: str, source_type: str):
        """
        Initialize monitor
        
        Args:
            name: Monitor name for logging
            source_type: Type of source (news, regulatory, tender, financial)
        """
        self.name = name
        self.source_type = source_type
        self.logger = logging.getLogger(f"{__name__}.{name}")
        self.last_run: Optional[datetime] = None
        self.results: List[TriggerResult] = []
    
    @abstractmethod
    def fetch(self) -> Any:
        """
        Fetch raw data from the source
        
        Returns:
            Raw data from source (format depends on implementation)
        """
        pass
    
    @abstractmethod
    def parse(self, raw_data: Any) -> List[Dict[str, Any]]:
        """
        Parse raw data into structured format
        
        Args:
            raw_data: Raw data from fetch()
            
        Returns:
            List of parsed items
        """
        pass
    
    @abstractmethod
    def analyze(self, items: List[Dict[str, Any]]) -> List[TriggerResult]:
        """
        Analyze parsed items for triggers
        
        Args:
            items: Parsed items from parse()
            
        Returns:
            List of trigger results
        """
        pass
    
    def run(self) -> List[TriggerResult]:
        """
        Execute full monitoring cycle: fetch -> parse -> analyze
        
        Returns:
            List of detected triggers
        """
        self.logger.info(f"Starting {self.name} monitor run")
        self.results = []
        
        try:
            # Fetch raw data
            self.logger.debug(f"Fetching data from {self.name}")
            raw_data = self.fetch()
            
            if not raw_data:
                self.logger.warning(f"No data fetched from {self.name}")
                return []
            
            # Parse data
            self.logger.debug(f"Parsing data from {self.name}")
            items = self.parse(raw_data)
            
            if not items:
                self.logger.warning(f"No items parsed from {self.name}")
                return []
            
            self.logger.info(f"Parsed {len(items)} items from {self.name}")
            
            # Analyze for triggers
            self.logger.debug(f"Analyzing {len(items)} items for triggers")
            self.results = self.analyze(items)
            
            self.logger.info(f"Found {len(self.results)} triggers from {self.name}")
            
        except Exception as e:
            self.logger.error(f"Error in {self.name} monitor: {e}", exc_info=True)
        
        finally:
            self.last_run = datetime.now()
        
        return self.results
    
    def get_results(self) -> List[TriggerResult]:
        """Get results from last run"""
        return self.results
    
    def get_stats(self) -> Dict[str, Any]:
        """Get monitor statistics"""
        return {
            "name": self.name,
            "source_type": self.source_type,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "results_count": len(self.results),
        }
