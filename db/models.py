"""
Database Models for PhoneTracker CLI

SQLAlchemy models for storing tracking history and authorization logs.
Database: SQLite stored at ~/.phonetracker/history.db
"""

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

Base = declarative_base()


class TrackingLog(Base):
    """
    Model for storing phone tracking history.
    
    Each record represents one tracking attempt with location data.
    """
    __tablename__ = 'tracking_logs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    phone_number = Column(String(20), nullable=False, index=True)
    call_sid = Column(String(50), nullable=True)  # Twilio call SID
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    accuracy = Column(Float, nullable=True)  # Accuracy in meters
    method = Column(String(50), nullable=True)  # Method used to get location
    city = Column(String(100), nullable=True)
    country = Column(String(100), nullable=True)
    carrier = Column(String(100), nullable=True)
    call_status = Column(String(20), nullable=True)  # answered, no-answer, busy, etc.
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    notes = Column(Text, nullable=True)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert record to dictionary."""
        return {
            'id': self.id,
            'phone_number': self.phone_number,
            'call_sid': self.call_sid,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'accuracy': self.accuracy,
            'method': self.method,
            'city': self.city,
            'country': self.country,
            'carrier': self.carrier,
            'call_status': self.call_status,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'notes': self.notes
        }
    
    def __repr__(self):
        return f"<TrackingLog(id={self.id}, phone={self.phone_number}, location={self.latitude},{self.longitude})>"


class AuthLog(Base):
    """
    Model for storing authorization and audit logs.
    
    Records all tracking attempts for compliance and auditing purposes.
    """
    __tablename__ = 'auth_logs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    action = Column(String(50), nullable=False)  # track, view_history, config_change, etc.
    phone_number = Column(String(20), nullable=True)
    user = Column(String(100), nullable=True)  # System user who ran the command
    ip_address = Column(String(45), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    success = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)
    details = Column(Text, nullable=True)  # Additional JSON details
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert record to dictionary."""
        return {
            'id': self.id,
            'action': self.action,
            'phone_number': self.phone_number,
            'user': self.user,
            'ip_address': self.ip_address,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'success': self.success,
            'error_message': self.error_message,
            'details': self.details
        }
    
    def __repr__(self):
        return f"<AuthLog(id={self.id}, action={self.action}, success={self.success})>"


class Database:
    """
    Database manager for PhoneTracker.
    
    Handles all database operations including creating tables,
    adding records, and querying history.
    """
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize database connection.
        
        Args:
            db_path: Path to SQLite database file. If None, uses default location.
        """
        if db_path is None:
            db_path = Path.home() / '.phonetracker' / 'history.db'
        
        # Ensure directory exists
        db_path = Path(db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create engine and session
        self.engine = create_engine(f'sqlite:///{db_path}', echo=False)
        Base.metadata.create_all(self.engine)
        
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
    
    def add_tracking_log(
        self,
        phone_number: str,
        call_sid: Optional[str] = None,
        location: Optional[Dict[str, Any]] = None,
        call_status: Optional[str] = None,
        notes: Optional[str] = None
    ) -> TrackingLog:
        """
        Add a new tracking log entry.
        
        Args:
            phone_number: The tracked phone number
            call_sid: Twilio call SID (if applicable)
            location: Location data dictionary
            call_status: Status of the call
            notes: Additional notes
            
        Returns:
            Created TrackingLog object
        """
        log = TrackingLog(
            phone_number=phone_number,
            call_sid=call_sid,
            latitude=location.get('latitude') if location else None,
            longitude=location.get('longitude') if location else None,
            accuracy=location.get('accuracy') if location else None,
            method=location.get('method') if location else None,
            city=location.get('city') if location else None,
            country=location.get('country') if location else None,
            carrier=location.get('carrier') if location else None,
            call_status=call_status,
            notes=notes
        )
        
        self.session.add(log)
        self.session.commit()
        return log
    
    def add_auth_log(
        self,
        action: str,
        phone_number: Optional[str] = None,
        user: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        details: Optional[str] = None
    ) -> AuthLog:
        """
        Add an authorization/audit log entry.
        
        Args:
            action: The action performed (e.g., 'track', 'view_history')
            phone_number: Phone number involved (if applicable)
            user: System user who performed the action
            success: Whether the action succeeded
            error_message: Error message if failed
            details: Additional details (JSON string)
            
        Returns:
            Created AuthLog object
        """
        import os
        import getpass
        
        log = AuthLog(
            action=action,
            phone_number=phone_number,
            user=user or getpass.getuser(),
            success=success,
            error_message=error_message,
            details=details
        )
        
        self.session.add(log)
        self.session.commit()
        return log
    
    def get_history(
        self,
        phone_number: Optional[str] = None,
        limit: int = 10,
        offset: int = 0
    ) -> List[TrackingLog]:
        """
        Get tracking history, optionally filtered by phone number.
        
        Args:
            phone_number: Filter by this phone number (optional)
            limit: Maximum number of records to return
            offset: Number of records to skip
            
        Returns:
            List of TrackingLog objects
        """
        query = self.session.query(TrackingLog)
        
        if phone_number:
            query = query.filter(TrackingLog.phone_number == phone_number)
        
        return query.order_by(TrackingLog.timestamp.desc()).offset(offset).limit(limit).all()
    
    def get_auth_logs(
        self,
        action: Optional[str] = None,
        limit: int = 50
    ) -> List[AuthLog]:
        """
        Get authorization logs.
        
        Args:
            action: Filter by action type (optional)
            limit: Maximum number of records to return
            
        Returns:
            List of AuthLog objects
        """
        query = self.session.query(AuthLog)
        
        if action:
            query = query.filter(AuthLog.action == action)
        
        return query.order_by(AuthLog.timestamp.desc()).limit(limit).all()
    
    def get_tracking_count(self, phone_number: Optional[str] = None) -> int:
        """Get total count of tracking records."""
        query = self.session.query(TrackingLog)
        if phone_number:
            query = query.filter(TrackingLog.phone_number == phone_number)
        return query.count()
    
    def delete_history(self, phone_number: Optional[str] = None) -> int:
        """
        Delete tracking history.
        
        Args:
            phone_number: Delete only records for this number (optional)
                         If None, deletes ALL records.
                         
        Returns:
            Number of records deleted
        """
        query = self.session.query(TrackingLog)
        
        if phone_number:
            query = query.filter(TrackingLog.phone_number == phone_number)
        
        count = query.count()
        query.delete()
        self.session.commit()
        
        return count
    
    def export_history(
        self,
        format: str = 'json',
        phone_number: Optional[str] = None
    ) -> str:
        """
        Export tracking history to JSON or CSV format.
        
        Args:
            format: Export format ('json' or 'csv')
            phone_number: Filter by phone number (optional)
            
        Returns:
            Exported data as string
        """
        records = self.get_history(phone_number=phone_number, limit=10000)
        
        if format == 'json':
            import json
            return json.dumps([r.to_dict() for r in records], indent=2)
        
        elif format == 'csv':
            import csv
            import io
            
            output = io.StringIO()
            if records:
                writer = csv.DictWriter(output, fieldnames=records[0].to_dict().keys())
                writer.writeheader()
                for record in records:
                    writer.writerow(record.to_dict())
            
            return output.getvalue()
        
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    def close(self):
        """Close the database session."""
        self.session.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
