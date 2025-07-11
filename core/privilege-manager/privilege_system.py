#!/usr/bin/env python3
"""
Privilege Management System for Autana Dojo
Controls access levels for different model types
"""

import json
import hashlib
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum
import os

class PrivilegeLevel(Enum):
    """Model privilege levels"""
    TRAINING = "training"      # Sandboxed, pattern discovery only
    DESKTOP = "desktop"        # Full system access
    RESTRICTED = "restricted"  # Custom limited access

class ModelPrivilegeSystem:
    """Manages model privileges and access control"""
    
    # Define privilege capabilities
    DESKTOP_PRIVILEGES = {
        'file_system_read': True,
        'file_system_write': True,
        'network_access': True,
        'system_commands': True,
        'deployment': True,
        'external_api': True,
        'pattern_discovery': True,
        'model_training': True,
        'data_export': True
    }
    
    TRAINING_PRIVILEGES = {
        'file_system_read': False,
        'file_system_write': False,
        'network_access': False,
        'system_commands': False,
        'deployment': False,
        'external_api': False,
        'pattern_discovery': True,
        'model_training': True,
        'data_export': False
    }
    
    def __init__(self, db_path: str = "privilege_registry.db"):
        self.db_path = db_path
        self.init_database()
        self.audit_log = []
        
    def init_database(self):
        """Initialize privilege registry database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Model registry
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS model_registry (
                model_id TEXT PRIMARY KEY,
                model_name TEXT NOT NULL,
                privilege_level TEXT NOT NULL,
                custom_privileges TEXT,
                created_at TIMESTAMP,
                created_by TEXT,
                last_modified TIMESTAMP,
                is_active BOOLEAN DEFAULT 1
            )
        ''')
        
        # Privilege audit log
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS privilege_audit (
                audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
                model_id TEXT,
                action TEXT,
                old_privilege TEXT,
                new_privilege TEXT,
                reason TEXT,
                approved_by TEXT,
                timestamp TIMESTAMP,
                FOREIGN KEY (model_id) REFERENCES model_registry(model_id)
            )
        ''')
        
        # Capability usage tracking
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS capability_usage (
                usage_id INTEGER PRIMARY KEY AUTOINCREMENT,
                model_id TEXT,
                capability TEXT,
                usage_count INTEGER DEFAULT 0,
                last_used TIMESTAMP,
                blocked_attempts INTEGER DEFAULT 0,
                FOREIGN KEY (model_id) REFERENCES model_registry(model_id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def register_model(self, model_name: str, privilege_level: PrivilegeLevel,
                      created_by: str = "system", custom_privileges: Optional[Dict] = None) -> str:
        """Register a new model with specified privileges"""
        model_id = self._generate_model_id(model_name)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO model_registry 
            (model_id, model_name, privilege_level, custom_privileges, 
             created_at, created_by, last_modified)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            model_id,
            model_name,
            privilege_level.value,
            json.dumps(custom_privileges) if custom_privileges else None,
            datetime.now().isoformat(),
            created_by,
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
        
        # Log registration
        self._audit_action(model_id, "REGISTERED", None, privilege_level.value,
                          f"Model registered by {created_by}", created_by)
        
        return model_id
    
    def check_privilege(self, model_id: str, capability: str) -> bool:
        """Check if model has specific capability"""
        privileges = self.get_model_privileges(model_id)
        
        if not privileges:
            return False
        
        # Track usage attempt
        self._track_capability_usage(model_id, capability, 
                                   allowed=privileges.get(capability, False))
        
        return privileges.get(capability, False)
    
    def get_model_privileges(self, model_id: str) -> Optional[Dict[str, bool]]:
        """Get all privileges for a model"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT privilege_level, custom_privileges 
            FROM model_registry 
            WHERE model_id = ? AND is_active = 1
        ''', (model_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return None
        
        privilege_level, custom_privileges = result
        
        # Base privileges
        if privilege_level == PrivilegeLevel.DESKTOP.value:
            privileges = self.DESKTOP_PRIVILEGES.copy()
        elif privilege_level == PrivilegeLevel.TRAINING.value:
            privileges = self.TRAINING_PRIVILEGES.copy()
        else:  # RESTRICTED
            privileges = self.TRAINING_PRIVILEGES.copy()
        
        # Apply custom privileges if any
        if custom_privileges:
            custom = json.loads(custom_privileges)
            privileges.update(custom)
        
        return privileges
    
    def request_privilege_escalation(self, model_id: str, 
                                   new_level: PrivilegeLevel,
                                   reason: str,
                                   requested_by: str = "system") -> str:
        """Request privilege escalation for a model"""
        request_id = f"req_{model_id}_{datetime.now().timestamp()}"
        
        # In a real system, this would create a pending request
        # For now, we'll log it
        self._audit_action(model_id, "ESCALATION_REQUESTED", 
                          None, new_level.value, reason, requested_by)
        
        print(f"⚠️  Privilege escalation requested for {model_id}")
        print(f"   Reason: {reason}")
        print(f"   New level: {new_level.value}")
        print(f"   Request ID: {request_id}")
        
        return request_id
    
    def approve_privilege_escalation(self, model_id: str, 
                                   new_level: PrivilegeLevel,
                                   approved_by: str,
                                   reason: str) -> bool:
        """Approve and apply privilege escalation"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get current level
        cursor.execute('''
            SELECT privilege_level FROM model_registry WHERE model_id = ?
        ''', (model_id,))
        
        result = cursor.fetchone()
        if not result:
            conn.close()
            return False
        
        old_level = result[0]
        
        # Update privilege level
        cursor.execute('''
            UPDATE model_registry 
            SET privilege_level = ?, last_modified = ?
            WHERE model_id = ?
        ''', (new_level.value, datetime.now().isoformat(), model_id))
        
        conn.commit()
        conn.close()
        
        # Audit the change
        self._audit_action(model_id, "ESCALATION_APPROVED", 
                          old_level, new_level.value, reason, approved_by)
        
        return True
    
    def create_sandboxed_environment(self, model_id: str) -> Dict[str, Any]:
        """Create sandboxed environment for training models"""
        privileges = self.get_model_privileges(model_id)
        
        if not privileges:
            return {"error": "Model not found"}
        
        # Define sandbox restrictions
        sandbox = {
            "model_id": model_id,
            "environment": "sandboxed",
            "allowed_operations": [
                key for key, allowed in privileges.items() if allowed
            ],
            "blocked_operations": [
                key for key, allowed in privileges.items() if not allowed
            ],
            "resource_limits": {
                "max_memory_mb": 512,
                "max_cpu_percent": 25,
                "max_runtime_seconds": 300,
                "allowed_imports": [
                    "numpy", "math", "json", "hashlib",
                    "collections", "itertools", "functools"
                ]
            }
        }
        
        return sandbox
    
    def _generate_model_id(self, model_name: str) -> str:
        """Generate unique model ID"""
        timestamp = datetime.now().isoformat()
        return hashlib.md5(f"{model_name}_{timestamp}".encode()).hexdigest()[:12]
    
    def _audit_action(self, model_id: str, action: str, 
                     old_privilege: Optional[str], new_privilege: str,
                     reason: str, actor: str):
        """Log privilege-related actions"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO privilege_audit
            (model_id, action, old_privilege, new_privilege, reason, approved_by, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            model_id, action, old_privilege, new_privilege, 
            reason, actor, datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    def _track_capability_usage(self, model_id: str, capability: str, allowed: bool):
        """Track capability usage attempts"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if allowed:
            cursor.execute('''
                INSERT INTO capability_usage (model_id, capability, usage_count, last_used)
                VALUES (?, ?, 1, ?)
                ON CONFLICT(model_id, capability) DO UPDATE SET
                usage_count = usage_count + 1,
                last_used = ?
            ''', (model_id, capability, datetime.now().isoformat(), 
                  datetime.now().isoformat()))
        else:
            cursor.execute('''
                INSERT INTO capability_usage (model_id, capability, blocked_attempts, last_used)
                VALUES (?, ?, 1, ?)
                ON CONFLICT(model_id, capability) DO UPDATE SET
                blocked_attempts = blocked_attempts + 1,
                last_used = ?
            ''', (model_id, capability, datetime.now().isoformat(),
                  datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
    
    def get_privilege_report(self, model_id: str) -> Dict[str, Any]:
        """Generate privilege usage report for a model"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get model info
        cursor.execute('''
            SELECT model_name, privilege_level, created_at, is_active
            FROM model_registry WHERE model_id = ?
        ''', (model_id,))
        
        model_info = cursor.fetchone()
        if not model_info:
            return {"error": "Model not found"}
        
        # Get usage stats
        cursor.execute('''
            SELECT capability, usage_count, blocked_attempts, last_used
            FROM capability_usage WHERE model_id = ?
        ''', (model_id,))
        
        usage_stats = cursor.fetchall()
        
        # Get audit history
        cursor.execute('''
            SELECT action, old_privilege, new_privilege, reason, timestamp
            FROM privilege_audit WHERE model_id = ?
            ORDER BY timestamp DESC LIMIT 10
        ''', (model_id,))
        
        audit_history = cursor.fetchall()
        
        conn.close()
        
        return {
            "model_id": model_id,
            "model_name": model_info[0],
            "privilege_level": model_info[1],
            "created_at": model_info[2],
            "is_active": bool(model_info[3]),
            "usage_statistics": [
                {
                    "capability": stat[0],
                    "usage_count": stat[1],
                    "blocked_attempts": stat[2],
                    "last_used": stat[3]
                } for stat in usage_stats
            ],
            "recent_audit_events": [
                {
                    "action": event[0],
                    "old_privilege": event[1],
                    "new_privilege": event[2],
                    "reason": event[3],
                    "timestamp": event[4]
                } for event in audit_history
            ]
        }


if __name__ == "__main__":
    # Demo the privilege system
    print("🔐 Autana Dojo Privilege System Demo")
    print("=" * 50)
    
    # Initialize system
    priv_system = ModelPrivilegeSystem()
    
    # Register models with different privileges
    print("\n📝 Registering models...")
    
    # Training model (sandboxed)
    training_model_id = priv_system.register_model(
        "pattern_discovery_specialist",
        PrivilegeLevel.TRAINING,
        created_by="dojo_admin"
    )
    print(f"✅ Training model registered: {training_model_id}")
    
    # Desktop model (full access)
    desktop_model_id = priv_system.register_model(
        "deployment_specialist",
        PrivilegeLevel.DESKTOP,
        created_by="dojo_admin"
    )
    print(f"✅ Desktop model registered: {desktop_model_id}")
    
    # Check privileges
    print("\n🔍 Checking privileges...")
    
    # Training model tries file access
    can_access_files = priv_system.check_privilege(training_model_id, "file_system_write")
    print(f"Training model file access: {can_access_files}")
    
    # Training model tries pattern discovery
    can_discover = priv_system.check_privilege(training_model_id, "pattern_discovery")
    print(f"Training model pattern discovery: {can_discover}")
    
    # Desktop model tries deployment
    can_deploy = priv_system.check_privilege(desktop_model_id, "deployment")
    print(f"Desktop model deployment: {can_deploy}")
    
    # Request escalation
    print("\n📈 Requesting privilege escalation...")
    request_id = priv_system.request_privilege_escalation(
        training_model_id,
        PrivilegeLevel.DESKTOP,
        "Model has proven stable and needs file access for production",
        requested_by="user"
    )
    
    # Approve escalation
    print("\n✅ Approving escalation...")
    priv_system.approve_privilege_escalation(
        training_model_id,
        PrivilegeLevel.DESKTOP,
        approved_by="admin",
        reason="Model passed all safety checks"
    )
    
    # Check new privileges
    can_access_now = priv_system.check_privilege(training_model_id, "file_system_write")
    print(f"Training model file access after escalation: {can_access_now}")
    
    # Generate report
    print("\n📊 Privilege Report:")
    report = priv_system.get_privilege_report(training_model_id)
    print(json.dumps(report, indent=2))