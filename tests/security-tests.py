# tests/security_tests.py

import asyncio
import jwt
import uuid
import re
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import secrets
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext

from tests.test_db import TestDatabase
from tests.test_config import TestData
from utils.logger import CustomLogger

logger = CustomLogger("security_tests", "security_tests.log")

class SecurityTests:
    """Comprehensive security testing suite"""
    
    def __init__(self):
        self.db = TestDatabase()
        self.test_data = TestData()
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self.oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
        self.secret_key = "test_secret_key_for_testing_only"
        
        # Track test users and sessions
        self.test_users: Dict[str, Dict[str, Any]] = {}
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        self.failed_login_attempts: Dict[str, List[datetime]] = {}
        
    async def setup(self):
        """Setup test environment"""
        self.db.setup()
        
        # Add security-specific tables
        self.db.cursor.executescript("""
            -- Session tracking
            CREATE TABLE IF NOT EXISTS user_sessions (
                session_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                token TEXT NOT NULL,
                device_info TEXT,
                ip_address TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
            
            -- Login attempts tracking
            CREATE TABLE IF NOT EXISTS login_attempts (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                email TEXT,
                ip_address TEXT,
                success BOOLEAN,
                attempt_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                error_message TEXT
            );
            
            -- Security audit log
            CREATE TABLE IF NOT EXISTS security_audit_log (
                id TEXT PRIMARY KEY,
                event_type TEXT NOT NULL,
                user_id TEXT,
                ip_address TEXT,
                details TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            -- API keys
            CREATE TABLE IF NOT EXISTS api_keys (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                key_hash TEXT NOT NULL,
                name TEXT,
                permissions TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                last_used TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
        """)
        
        self.db.conn.commit()
        logger.info("Security test environment setup complete")

    async def test_password_security(self):
        """Test password hashing and validation"""
        logger.info("Testing password security...")
        
        # Test password hashing
        passwords = [
            "SimplePass123",  # Basic password
            "C0mpl3x!P@ssw0rd",  # Complex password
            "使用漢字アルファベット",  # Unicode password
            "   Space Padded   ",  # Spaces
            "a" * 100  # Very long password
        ]
        
        for password in passwords:
            # Hash password
            hashed = self.pwd_context.hash(password)
            
            # Verify hash properties
            assert len(hashed) > 50, "Hash too short"
            assert not hashed.startswith(password), "Clear text in hash"
            
            # Verify password
            assert self.pwd_context.verify(password, hashed), "Verification failed"
            assert not self.pwd_context.verify(password + "x", hashed), "False positive"
            
            # Verify hash uniqueness
            hashed2 = self.pwd_context.hash(password)
            assert hashed != hashed2, "Hash not unique"

    async def test_token_security(self):
        """Test JWT token generation and validation"""
        logger.info("Testing token security...")
        
        # Create test user
        user_id = str(uuid.uuid4())
        test_user = {
            "id": user_id,
            "username": "security_test_user",
            "email": "security@test.com",
            "role": "user"
        }
        
        # Test token generation
        token_data = {
            "sub": user_id,
            "username": test_user["username"],
            "role": test_user["role"],
            "exp": datetime.utcnow() + timedelta(minutes=30)
        }
        token = jwt.encode(token_data, self.secret_key, algorithm="HS256")
        
        # Verify token
        decoded = jwt.decode(token, self.secret_key, algorithms=["HS256"])
        assert decoded["sub"] == user_id
        assert decoded["username"] == test_user["username"]
        
        # Test token expiration
        expired_token_data = token_data.copy()
        expired_token_data["exp"] = datetime.utcnow() - timedelta(minutes=1)
        expired_token = jwt.encode(expired_token_data, self.secret_key, algorithm="HS256")
        
        try:
            jwt.decode(expired_token, self.secret_key, algorithms=["HS256"])
            assert False, "Expired token not caught"
        except jwt.ExpiredSignatureError:
            pass

    async def test_session_management(self):
        """Test session creation, validation, and expiration"""
        logger.info("Testing session management...")
        
        # Create test user and session
        user_id = str(uuid.uuid4())
        session_id = str(uuid.uuid4())
        device_info = {"device": "test_device", "os": "test_os"}
        
        # Create session
        self.db.cursor.execute("""
            INSERT INTO user_sessions 
            (session_id, user_id, token, device_info, expires_at, is_active)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            session_id,
            user_id,
            "test_token",
            str(device_info),
            (datetime.utcnow() + timedelta(hours=1)).timestamp(),
            True
        ))
        
        # Test session validation
        self.db.cursor.execute("""
            SELECT * FROM user_sessions 
            WHERE session_id = ? AND is_active = 1 
            AND expires_at > ?
        """, (session_id, datetime.utcnow().timestamp()))
        
        session = self.db.cursor.fetchone()
        assert session is not None, "Session not found"
        
        # Test session expiration
        self.db.cursor.execute("""
            UPDATE user_sessions 
            SET expires_at = ? 
            WHERE session_id = ?
        """, ((datetime.utcnow() - timedelta(minutes=1)).timestamp(), session_id))
        
        self.db.cursor.execute("""
            SELECT * FROM user_sessions 
            WHERE session_id = ? AND is_active = 1 
            AND expires_at > ?
        """, (session_id, datetime.utcnow().timestamp()))
        
        expired_session = self.db.cursor.fetchone()
        assert expired_session is None, "Expired session still valid"

    async def test_rate_limiting(self):
        """Test login attempt rate limiting"""
        logger.info("Testing rate limiting...")
        
        email = "ratelimit@test.com"
        ip_address = "192.168.1.1"
        window_minutes = 5
        max_attempts = 5
        
        # Simulate multiple login attempts
        for i in range(max_attempts + 2):
            self.db.cursor.execute("""
                INSERT INTO login_attempts 
                (id, email, ip_address, success, error_message)
                VALUES (?, ?, ?, ?, ?)
            """, (
                str(uuid.uuid4()),
                email,
                ip_address,
                False,
                "Invalid password"
            ))
        
        # Check if account is locked
        self.db.cursor.execute("""
            SELECT COUNT(*) FROM login_attempts 
            WHERE email = ? AND success = 0 
            AND attempt_time > ? 
        """, (email, (datetime.utcnow() - timedelta(minutes=window_minutes)).timestamp()))
        
        failed_attempts = self.db.cursor.fetchone()[0]
        assert failed_attempts > max_attempts, "Rate limiting not triggered"

    async def test_api_key_security(self):
        """Test API key generation and validation"""
        logger.info("Testing API key security...")
        
        # Generate API key
        api_key = secrets.token_urlsafe(32)
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        
        # Store API key
        self.db.cursor.execute("""
            INSERT INTO api_keys 
            (id, user_id, key_hash, name, permissions)
            VALUES (?, ?, ?, ?, ?)
        """, (
            str(uuid.uuid4()),
            "test_user",
            key_hash,
            "Test API Key",
            '{"read": true, "write": false}'
        ))
        
        # Validate API key
        self.db.cursor.execute("""
            SELECT * FROM api_keys 
            WHERE key_hash = ? AND is_active = 1
        """, (key_hash,))
        
        stored_key = self.db.cursor.fetchone()
        assert stored_key is not None, "API key not found"
        
        # Test key validation
        def validate_api_key(key: str) -> bool:
            test_hash = hashlib.sha256(key.encode()).hexdigest()
            return test_hash == key_hash
        
        assert validate_api_key(api_key), "Valid key not accepted"
        assert not validate_api_key(api_key + "x"), "Invalid key accepted"

    async def test_permission_security(self):
        """Test role-based access control"""
        logger.info("Testing permission security...")
        
        # Create users with different roles
        roles = {
            "admin": {"manage_users", "manage_system", "view_all"},
            "agent_creator": {"create_agent", "view_own"},
            "user": {"view_own"}
        }
        
        for role, permissions in roles.items():
            user_id = str(uuid.uuid4())
            self.db.cursor.execute("""
                INSERT INTO users (id, username, email, role)
                VALUES (?, ?, ?, ?)
            """, (
                user_id,
                f"{role}_user",
                f"{role}@test.com",
                role
            ))
            
            # Test permissions
            for action in {"manage_users", "create_agent", "view_own"}:
                has_permission = action in permissions
                assert has_permission == self._check_permission(role, action), \
                    f"Permission check failed for {role} - {action}"

    def _check_permission(self, role: str, action: str) -> bool:
        """Check if role has permission for action"""
        permission_matrix = {
            "admin": {"manage_users", "manage_system", "view_all", "create_agent", "view_own"},
            "agent_creator": {"create_agent", "view_own"},
            "user": {"view_own"}
        }
        return action in permission_matrix.get(role, set())

    async def test_input_validation(self):
        """Test input validation and sanitization"""
        logger.info("Testing input validation...")
        
        # Test email validation
        valid_emails = [
            "test@example.com",
            "user.name+tag@domain.com",
            "x@y.z"
        ]
        
        invalid_emails = [
            "not_an_email",
            "@nodomain.com",
            "space in@email.com",
            "missing@.com"
        ]
        
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        for email in valid_emails:
            assert re.match(email_pattern, email), f"Valid email rejected: {email}"
        
        for email in invalid_emails:
            assert not re.match(email_pattern, email), f"Invalid email accepted: {email}"
        
        # Test SQL injection prevention
        dangerous_inputs = [
            "' OR '1'='1",
            "; DROP TABLE users;--",
            "' UNION SELECT * FROM passwords;--"
        ]
        
        for dangerous_input in dangerous_inputs:
            # Use parameterized query
            self.db.cursor.execute(
                "SELECT * FROM users WHERE username = ?",
                (dangerous_input,)
            )
            result = self.db.cursor.fetchall()
            assert len(result) == 0, "SQL injection may be possible"

    async def run_all_tests(self):
        """Run all security tests"""
        test_methods = [
            self.test_password_security,
            self.test_token_security,
            self.test_session_management,
            self.test_rate_limiting,
            self.test_api_key_security,
            self.test_permission_security,
            self.test_input_validation
        ]
        
        results = []
        for test_method in test_methods:
            try:
                await test_method()
                results.append((test_method.__name__, "PASSED", None))
                logger.info(f"{test_method.__name__} passed")
            except Exception as e:
                results.append((test_method.__name__, "FAILED", str(e)))
                logger.error(f"{test_method.__name__} failed: {str(e)}")
        
        return results

    async def cleanup(self):
        """Cleanup test environment"""
        self.db.cleanup()
        logger.info("Security test cleanup complete")

async def run_security_tests():
    """Run all security tests"""
    test_suite = SecurityTests()
    try:
        await test_suite.setup()
        results = await test_suite.run_all_tests()
        
        # Print results
        print("\nSecurity Test Results:")
        print("=====================")
        for test_name, status, error in results:
            status_symbol = "✓" if status == "PASSED" else "✗"
            print(f"{status_symbol} {test_name}")
            if error:
                print(f"  Error: {error}")
        
        passed = sum(1 for _, status, _ in results if status == "PASSED")
        total = len(results)
        print(f"\nPassed {passed}/{total} tests")
        
        return passed == total
        
    finally:
        await test_suite.cleanup()

if __name__ == "__main__":
    success = asyncio.run(run_security_tests())
    import sys
    sys.exit(0 if success else 1)
