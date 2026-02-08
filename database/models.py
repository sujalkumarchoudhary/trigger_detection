"""
Database models for Trigger Detection System
"""
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional, List, Dict, Any
import json


@dataclass
class TriggerEvent:
    """Base trigger event stored in database"""
    id: Optional[int] = None
    source_type: str = ""  # news, regulatory, tender, financial
    source_name: str = ""
    title: str = ""
    content: str = ""
    url: str = ""
    company_name: Optional[str] = None
    trigger_keywords: str = ""  # JSON list
    sentiment_score: float = 0.0
    trigger_score: float = 0.0
    detected_at: Optional[datetime] = None
    published_at: Optional[datetime] = None
    is_processed: bool = False
    is_archived: bool = False
    notes: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        d = asdict(self)
        d['detected_at'] = self.detected_at.isoformat() if self.detected_at else None
        d['published_at'] = self.published_at.isoformat() if self.published_at else None
        return d
    
    def get_keywords_list(self) -> List[str]:
        """Get trigger keywords as list"""
        try:
            return json.loads(self.trigger_keywords) if self.trigger_keywords else []
        except json.JSONDecodeError:
            return []
    
    def set_keywords_list(self, keywords: List[str]):
        """Set trigger keywords from list"""
        self.trigger_keywords = json.dumps(keywords)


@dataclass
class NewsItem:
    """News item from RSS or Google News"""
    id: Optional[int] = None
    trigger_id: Optional[int] = None
    source: str = ""
    title: str = ""
    summary: str = ""
    url: str = ""
    published_at: Optional[datetime] = None
    sentiment_label: str = ""
    sentiment_polarity: float = 0.0
    created_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d['published_at'] = self.published_at.isoformat() if self.published_at else None
        d['created_at'] = self.created_at.isoformat() if self.created_at else None
        return d


@dataclass
class TenderItem:
    """Tender/contract item"""
    id: Optional[int] = None
    trigger_id: Optional[int] = None
    source: str = ""
    title: str = ""
    description: str = ""
    organization: str = ""
    estimated_value: float = 0.0
    quantity: str = ""
    quantity_scale: str = ""
    deadline: Optional[datetime] = None
    url: str = ""
    status: str = "active"
    created_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d['deadline'] = self.deadline.isoformat() if self.deadline else None
        d['created_at'] = self.created_at.isoformat() if self.created_at else None
        return d


@dataclass
class RegulatoryUpdate:
    """Regulatory update (approval, alert, patent)"""
    id: Optional[int] = None
    trigger_id: Optional[int] = None
    source: str = ""
    update_type: str = ""  # approval, warning, patent
    title: str = ""
    description: str = ""
    company_name: str = ""
    severity: str = ""
    url: str = ""
    effective_date: Optional[datetime] = None
    created_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d['effective_date'] = self.effective_date.isoformat() if self.effective_date else None
        d['created_at'] = self.created_at.isoformat() if self.created_at else None
        return d


@dataclass
class FinancialSignal:
    """Financial indicator signal"""
    id: Optional[int] = None
    trigger_id: Optional[int] = None
    company_name: str = ""
    signal_type: str = ""  # quarterly_result, stock_filing, job_signal, social_media
    title: str = ""
    description: str = ""
    signal_data: str = ""  # JSON data
    signal_strength: float = 0.0
    url: str = ""
    created_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d['created_at'] = self.created_at.isoformat() if self.created_at else None
        return d
    
    def get_signal_data(self) -> Dict[str, Any]:
        """Get signal data as dict"""
        try:
            return json.loads(self.signal_data) if self.signal_data else {}
        except json.JSONDecodeError:
            return {}
    
    def set_signal_data(self, data: Dict[str, Any]):
        """Set signal data from dict"""
        self.signal_data = json.dumps(data)
