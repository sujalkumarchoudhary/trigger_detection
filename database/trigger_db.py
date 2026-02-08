"""
SQLite Database operations for Trigger Detection System
"""
import sqlite3
import os
from datetime import datetime
from typing import List, Optional, Dict, Any
import json
import logging

from .models import TriggerEvent, NewsItem, TenderItem, RegulatoryUpdate, FinancialSignal
from config.trigger_config import DATABASE_PATH

logger = logging.getLogger(__name__)


class TriggerDatabase:
    """
    SQLite database for storing trigger detection results
    """
    
    def __init__(self, db_path: str = None):
        """Initialize database connection"""
        self.db_path = db_path or DATABASE_PATH
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        self._init_database()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_database(self):
        """Initialize database tables"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Create triggers table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS triggers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_type TEXT NOT NULL,
                source_name TEXT,
                title TEXT NOT NULL,
                content TEXT,
                url TEXT,
                company_name TEXT,
                trigger_keywords TEXT,
                sentiment_score REAL DEFAULT 0,
                trigger_score REAL DEFAULT 0,
                detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                published_at TIMESTAMP,
                is_processed INTEGER DEFAULT 0,
                is_archived INTEGER DEFAULT 0,
                notes TEXT,
                content_hash TEXT UNIQUE
            )
        ''')
        
        # Create news_items table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS news_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trigger_id INTEGER,
                source TEXT,
                title TEXT,
                summary TEXT,
                url TEXT,
                published_at TIMESTAMP,
                sentiment_label TEXT,
                sentiment_polarity REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (trigger_id) REFERENCES triggers(id)
            )
        ''')
        
        # Create tenders table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tenders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trigger_id INTEGER,
                source TEXT,
                title TEXT,
                description TEXT,
                organization TEXT,
                estimated_value REAL,
                quantity TEXT,
                quantity_scale TEXT,
                deadline TIMESTAMP,
                url TEXT,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (trigger_id) REFERENCES triggers(id)
            )
        ''')
        
        # Create regulatory_updates table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS regulatory_updates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trigger_id INTEGER,
                source TEXT,
                update_type TEXT,
                title TEXT,
                description TEXT,
                company_name TEXT,
                severity TEXT,
                url TEXT,
                effective_date TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (trigger_id) REFERENCES triggers(id)
            )
        ''')
        
        # Create financial_signals table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS financial_signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trigger_id INTEGER,
                company_name TEXT,
                signal_type TEXT,
                title TEXT,
                description TEXT,
                signal_data TEXT,
                signal_strength REAL,
                url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (trigger_id) REFERENCES triggers(id)
            )
        ''')
        
        # Create indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_triggers_source_type ON triggers(source_type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_triggers_score ON triggers(trigger_score DESC)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_triggers_company ON triggers(company_name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_triggers_detected ON triggers(detected_at DESC)')
        
        conn.commit()
        conn.close()
        
        logger.info(f"Database initialized at {self.db_path}")
    
    def _hash_content(self, content: str) -> str:
        """Generate hash for deduplication"""
        import hashlib
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def insert_trigger(self, trigger: TriggerEvent) -> Optional[int]:
        """
        Insert a trigger event into database
        
        Args:
            trigger: TriggerEvent to insert
            
        Returns:
            Inserted ID or None if duplicate
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Create content hash for deduplication
        content_hash = self._hash_content(f"{trigger.title}{trigger.content}{trigger.url}")
        
        try:
            cursor.execute('''
                INSERT INTO triggers (
                    source_type, source_name, title, content, url,
                    company_name, trigger_keywords, sentiment_score,
                    trigger_score, detected_at, published_at,
                    is_processed, is_archived, notes, content_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                trigger.source_type,
                trigger.source_name,
                trigger.title,
                trigger.content,
                trigger.url,
                trigger.company_name,
                trigger.trigger_keywords,
                trigger.sentiment_score,
                trigger.trigger_score,
                trigger.detected_at or datetime.now(),
                trigger.published_at,
                int(trigger.is_processed),
                int(trigger.is_archived),
                trigger.notes,
                content_hash,
            ))
            
            trigger_id = cursor.lastrowid
            conn.commit()
            logger.debug(f"Inserted trigger ID {trigger_id}")
            return trigger_id
            
        except sqlite3.IntegrityError:
            # Duplicate content
            logger.debug(f"Duplicate trigger skipped: {trigger.title[:50]}")
            return None
            
        finally:
            conn.close()
    
    def get_triggers(
        self,
        source_type: str = None,
        company_name: str = None,
        min_score: float = None,
        limit: int = 100,
        include_archived: bool = False,
    ) -> List[TriggerEvent]:
        """
        Get triggers from database with filters
        
        Args:
            source_type: Filter by source type
            company_name: Filter by company name
            min_score: Minimum trigger score
            limit: Maximum results
            include_archived: Include archived triggers
            
        Returns:
            List of TriggerEvent objects
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        query = "SELECT * FROM triggers WHERE 1=1"
        params = []
        
        if not include_archived:
            query += " AND is_archived = 0"
        
        if source_type:
            query += " AND source_type = ?"
            params.append(source_type)
        
        if company_name:
            query += " AND company_name LIKE ?"
            params.append(f"%{company_name}%")
        
        if min_score:
            query += " AND trigger_score >= ?"
            params.append(min_score)
        
        query += " ORDER BY trigger_score DESC, detected_at DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        triggers = []
        for row in rows:
            trigger = TriggerEvent(
                id=row['id'],
                source_type=row['source_type'],
                source_name=row['source_name'],
                title=row['title'],
                content=row['content'],
                url=row['url'],
                company_name=row['company_name'],
                trigger_keywords=row['trigger_keywords'],
                sentiment_score=row['sentiment_score'],
                trigger_score=row['trigger_score'],
                detected_at=datetime.fromisoformat(row['detected_at']) if row['detected_at'] else None,
                published_at=datetime.fromisoformat(row['published_at']) if row['published_at'] else None,
                is_processed=bool(row['is_processed']),
                is_archived=bool(row['is_archived']),
                notes=row['notes'],
            )
            triggers.append(trigger)
        
        return triggers
    
    def get_trigger_stats(self) -> Dict[str, Any]:
        """Get trigger statistics"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        stats = {}
        
        # Total triggers
        cursor.execute("SELECT COUNT(*) FROM triggers WHERE is_archived = 0")
        stats['total_triggers'] = cursor.fetchone()[0]
        
        # By source type
        cursor.execute("""
            SELECT source_type, COUNT(*) as count 
            FROM triggers WHERE is_archived = 0 
            GROUP BY source_type
        """)
        stats['by_source'] = {row['source_type']: row['count'] for row in cursor.fetchall()}
        
        # High score triggers (>= 7)
        cursor.execute("SELECT COUNT(*) FROM triggers WHERE trigger_score >= 7 AND is_archived = 0")
        stats['high_score_count'] = cursor.fetchone()[0]
        
        # Recent triggers (last 24 hours)
        cursor.execute("""
            SELECT COUNT(*) FROM triggers 
            WHERE detected_at >= datetime('now', '-1 day') AND is_archived = 0
        """)
        stats['recent_triggers'] = cursor.fetchone()[0]
        
        # Top companies
        cursor.execute("""
            SELECT company_name, COUNT(*) as count 
            FROM triggers 
            WHERE company_name IS NOT NULL AND is_archived = 0
            GROUP BY company_name 
            ORDER BY count DESC 
            LIMIT 10
        """)
        stats['top_companies'] = {row['company_name']: row['count'] for row in cursor.fetchall()}
        
        conn.close()
        return stats
    
    def mark_processed(self, trigger_id: int):
        """Mark trigger as processed"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE triggers SET is_processed = 1 WHERE id = ?", (trigger_id,))
        conn.commit()
        conn.close()
    
    def archive_trigger(self, trigger_id: int):
        """Archive a trigger"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE triggers SET is_archived = 1 WHERE id = ?", (trigger_id,))
        conn.commit()
        conn.close()
    
    def add_note(self, trigger_id: int, note: str):
        """Add note to trigger"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE triggers SET notes = ? WHERE id = ?", (note, trigger_id))
        conn.commit()
        conn.close()
    
    def export_to_csv(self, filepath: str, filters: Dict = None) -> int:
        """
        Export triggers to CSV
        
        Args:
            filepath: Output CSV path
            filters: Optional filters
            
        Returns:
            Number of rows exported
        """
        import csv
        
        triggers = self.get_triggers(**(filters or {}))
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Header
            writer.writerow([
                'ID', 'Source Type', 'Source Name', 'Title', 'Company',
                'Trigger Score', 'Sentiment', 'Keywords', 'URL', 'Detected At'
            ])
            
            # Data
            for t in triggers:
                writer.writerow([
                    t.id, t.source_type, t.source_name, t.title, t.company_name,
                    t.trigger_score, t.sentiment_score, t.trigger_keywords,
                    t.url, t.detected_at
                ])
        
        logger.info(f"Exported {len(triggers)} triggers to {filepath}")
        return len(triggers)
