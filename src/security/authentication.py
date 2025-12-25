#!/usr/bin/env python3
"""
Authentication and authorization system for fraud detection API.
Provides JWT-based authentication, role-based access control, and security middleware.
"""

import jwt

import secrets
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import logging


logger = logging.getLogger(__name__)


class UserRole(Enum):
    """User roles for authorization."""
    VIEWER = "viewer"           # Read-only access to dashboards
    OPERATOR = "operator"       # Can acknowledge/resolve alerts
    ANALYST = "analyst"         # Can view detailed analytics
    ADMIN = "admin"            # Full system access
    SYSTEM = "system"          # Internal system access


@dataclass
class User:
    """User data structure."""
    id: str
    username: str
    email: str
    role: UserRole
    is_active: bool = True
    created_at: datetime = None
    last_login: Optional[datetime] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Any]:
        """Convert user to dictionary."""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role.value,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat(),
            'last_login': self.last_login.isoformat() if self.last_login else None
        }


@dataclass
class Permission:
    """Permission data structure."""
    resource: str
    action: str
    roles: List[UserRole]

    def allows(self, role: UserRole, action: str = None) -> bool:
        """Check if role has permission for action."""
        if role not in self.roles:
            return False
        if action and action != self.action:
            return False
        return True


class SecurityConfig:
    """Security configuration."""

    def __init__(self):
        # JWT Configuration
        self.jwt_secret = self._get_jwt_secret()
        self.jwt_algorithm = "HS256"
        self.jwt_expiration_hours = 24

        # Password Configuration
        self.password_min_length = 8
        self.password_require_special = True
        self.password_require_numbers = True

        # Rate Limiting
        self.rate_limit_requests = 100  # requests per minute
        self.rate_limit_window = 60     # seconds

        # Session Configuration
        self.session_timeout_hours = 8
        self.max_failed_logins = 5
        self.lockout_duration_minutes = 30

    def _get_jwt_secret(self) -> str:
        """Get JWT secret from environment or generate one."""
        import os
        secret = os.getenv('JWT_SECRET')
        if not secret:
            secret = secrets.token_urlsafe(32)
            logger.warning("JWT_SECRET not set, using generated secret")
        return secret


class PasswordManager:
    """Password management utilities."""

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password using bcrypt."""
        import bcrypt
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        """Verify password against hash."""
        import bcrypt
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

    @staticmethod
    def validate_password(password: str, config: SecurityConfig) -> Dict[str, Any]:
        """Validate password strength."""
        errors = []

        if len(password) < config.password_min_length:
            errors.append(
                f"Password must be at least {config.password_min_length} characters")

        if config.password_require_numbers and not any(c.isdigit() for c in password):
            errors.append("Password must contain at least one number")

        if config.password_require_special and not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
            errors.append(
                "Password must contain at least one special character")

        return {
            'valid': len(errors) == 0,
            'errors': errors
        }


class JWTManager:
    """JWT token management."""

    def __init__(self, config: SecurityConfig):
        self.config = config

    def create_token(self, user: User) -> str:
        """Create JWT token for user."""
        payload = {
            'user_id': user.id,
            'username': user.username,
            'role': user.role.value,
            'exp': datetime.now(timezone.utc) + timedelta(hours=self.config.jwt_expiration_hours),
            'iat': datetime.now(timezone.utc)
        }

        return jwt.encode(payload, self.config.jwt_secret, algorithm=self.config.jwt_algorithm)

    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode JWT token."""
        try:
            payload = jwt.decode(token, self.config.jwt_secret, algorithms=[
                                 self.config.jwt_algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("JWT token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning("Invalid JWT token: %s", e)
            return None


class PermissionManager:
    """Permission management system."""

    def __init__(self):
        self.permissions = self._initialize_permissions()

    def _initialize_permissions(self) -> List[Permission]:
        """Initialize system permissions."""
        return [
            # Dashboard permissions
            Permission("dashboard", "read", [
                       UserRole.VIEWER, UserRole.OPERATOR, UserRole.ANALYST, UserRole.ADMIN]),
            Permission("dashboard", "write", [
                       UserRole.OPERATOR, UserRole.ANALYST, UserRole.ADMIN]),

            # Metrics permissions
            Permission("metrics", "read", [
                       UserRole.VIEWER, UserRole.OPERATOR, UserRole.ANALYST, UserRole.ADMIN]),
            Permission("metrics", "write", [UserRole.ANALYST, UserRole.ADMIN]),

            # Alert permissions
            Permission("alerts", "read", [
                       UserRole.VIEWER, UserRole.OPERATOR, UserRole.ANALYST, UserRole.ADMIN]),
            Permission("alerts", "acknowledge", [
                       UserRole.OPERATOR, UserRole.ANALYST, UserRole.ADMIN]),
            Permission("alerts", "resolve", [
                       UserRole.OPERATOR, UserRole.ANALYST, UserRole.ADMIN]),
            Permission("alerts", "create", [UserRole.ANALYST, UserRole.ADMIN]),

            # System permissions
            Permission("system", "read", [UserRole.ANALYST, UserRole.ADMIN]),
            Permission("system", "write", [UserRole.ADMIN]),
            Permission("system", "admin", [UserRole.ADMIN]),

            # User management
            Permission("users", "read", [UserRole.ADMIN]),
            Permission("users", "write", [UserRole.ADMIN]),
            Permission("users", "delete", [UserRole.ADMIN]),
        ]

    def check_permission(self, role: UserRole, resource: str, action: str) -> bool:
        """Check if role has permission for resource and action."""
        for permission in self.permissions:
            if permission.resource == resource and permission.action == action:
                return permission.allows(role)
        return False

    def get_user_permissions(self, role: UserRole) -> List[Dict[str, str]]:
        """Get all permissions for a role."""
        user_permissions = []
        for permission in self.permissions:
            if permission.allows(role):
                user_permissions.append({
                    'resource': permission.resource,
                    'action': permission.action
                })
        return user_permissions


class UserManager:
    """User management system."""

    def __init__(self):
        self.users: Dict[str, User] = {}
        self.password_manager = PasswordManager()
        self.failed_login_attempts: Dict[str, Dict[str, Any]] = {}
        self._initialize_default_users()

    def _initialize_default_users(self):
        """Initialize default system users."""
        default_users = [
            {
                'id': 'admin-001',
                'username': 'admin',
                'email': 'admin@frauddetection.com',
                'password': 'Admin123!',
                'role': UserRole.ADMIN
            },
            {
                'id': 'analyst-001',
                'username': 'analyst',
                'email': 'analyst@frauddetection.com',
                'password': 'Analyst123!',
                'role': UserRole.ANALYST
            },
            {
                'id': 'operator-001',
                'username': 'operator',
                'email': 'operator@frauddetection.com',
                'password': 'Operator123!',
                'role': UserRole.OPERATOR
            },
            {
                'id': 'viewer-001',
                'username': 'viewer',
                'email': 'viewer@frauddetection.com',
                'password': 'Viewer123!',
                'role': UserRole.VIEWER
            }
        ]

        for user_data in default_users:
            self.create_user(
                user_data['id'],
                user_data['username'],
                user_data['email'],
                user_data['password'],
                user_data['role']
            )

    def create_user(self, user_id: str, username: str, email: str,
                    password: str, role: UserRole) -> Optional[User]:
        """Create a new user."""
        if username in [u.username for u in self.users.values()]:
            logger.error("Username %s already exists", username)
            return None

        if email in [u.email for u in self.users.values()]:
            logger.error("Email %s already exists", email)
            return None

        # Validate password
        config = SecurityConfig()
        validation = self.password_manager.validate_password(password, config)
        if not validation['valid']:
            logger.error("Password validation failed: %s",
                         validation['errors'])
            return None

        # Hash password
        hashed_password = self.password_manager.hash_password(password)

        # Create user
        user = User(
            id=user_id,
            username=username,
            email=email,
            role=role
        )

        # Store user with hashed password
        self.users[user_id] = user
        self._store_password_hash(user_id, hashed_password)

        logger.info("Created user: %s with role %s", username, role.value)
        return user

    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Authenticate user with username and password."""
        # Find user by username
        user = None
        for u in self.users.values():
            if u.username == username:
                user = u
                break

        if not user:
            logger.warning(
                "Authentication failed: user %s not found", username)
            return None

        if not user.is_active:
            logger.warning(
                "Authentication failed: user %s is inactive", username)
            return None

        # Check for account lockout
        if self._is_account_locked(username):
            logger.warning(
                "Authentication failed: account %s is locked", username)
            return None

        # Verify password
        hashed_password = self._get_password_hash(user.id)
        if not hashed_password or not self.password_manager.verify_password(password, hashed_password):
            self._record_failed_login(username)
            logger.warning(
                "Authentication failed: invalid password for user %s", username)
            return None

        # Reset failed login attempts
        self._reset_failed_login_attempts(username)

        # Update last login
        user.last_login = datetime.now(timezone.utc)

        logger.info("User %s authenticated successfully", username)
        return user

    def _store_password_hash(self, user_id: str, hashed_password: str):
        """Store password hash (in production, use secure database)."""
        # This is a simplified implementation
        # In production, use a secure database with encryption
        import os
        password_file = f"passwords/{user_id}.hash"
        os.makedirs("passwords", exist_ok=True)
        with open(password_file, 'w', encoding='utf-8') as f:
            f.write(hashed_password)

    def _get_password_hash(self, user_id: str) -> Optional[str]:
        """Get password hash."""
        try:
            password_file = f"passwords/{user_id}.hash"
            with open(password_file, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except FileNotFoundError:
            return None

    def _record_failed_login(self, username: str):
        """Record failed login attempt."""
        if username not in self.failed_login_attempts:
            self.failed_login_attempts[username] = {
                'count': 0,
                'first_attempt': datetime.now(timezone.utc)
            }

        self.failed_login_attempts[username]['count'] += 1
        self.failed_login_attempts[username]['last_attempt'] = datetime.now(
            timezone.utc)

    def _reset_failed_login_attempts(self, username: str):
        """Reset failed login attempts."""
        if username in self.failed_login_attempts:
            del self.failed_login_attempts[username]

    def _is_account_locked(self, username: str) -> bool:
        """Check if account is locked due to failed login attempts."""
        if username not in self.failed_login_attempts:
            return False

        attempts = self.failed_login_attempts[username]
        config = SecurityConfig()

        if attempts['count'] >= config.max_failed_logins:
            lockout_time = attempts['last_attempt'] + \
                timedelta(minutes=config.lockout_duration_minutes)
            if datetime.now(timezone.utc) < lockout_time:
                return True
            else:
                # Lockout period expired
                self._reset_failed_login_attempts(username)

        return False

    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        return self.users.get(user_id)

    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        for user in self.users.values():
            if user.username == username:
                return user
        return None

    def list_users(self) -> List[User]:
        """List all users."""
        return list(self.users.values())


class SecurityManager:
    """Main security manager."""

    def __init__(self):
        self.config = SecurityConfig()
        self.jwt_manager = JWTManager(self.config)
        self.permission_manager = PermissionManager()
        self.user_manager = UserManager()

    def authenticate(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate user and return token."""
        user = self.user_manager.authenticate_user(username, password)
        if not user:
            return None

        token = self.jwt_manager.create_token(user)
        permissions = self.permission_manager.get_user_permissions(user.role)

        return {
            'token': token,
            'user': user.to_dict(),
            'permissions': permissions,
            'expires_in': self.config.jwt_expiration_hours * 3600
        }

    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify JWT token and return user info."""
        payload = self.jwt_manager.verify_token(token)
        if not payload:
            return None

        user = self.user_manager.get_user_by_id(payload['user_id'])
        if not user or not user.is_active:
            return None

        return {
            'user': user.to_dict(),
            'permissions': self.permission_manager.get_user_permissions(user.role)
        }

    def check_permission(self, token: str, resource: str, action: str) -> bool:
        """Check if token has permission for resource and action."""
        payload = self.jwt_manager.verify_token(token)
        if not payload:
            return False

        user = self.user_manager.get_user_by_id(payload['user_id'])
        if not user or not user.is_active:
            return False

        return self.permission_manager.check_permission(user.role, resource, action)

    def create_user(self, username: str, email: str, password: str, role: UserRole) -> Optional[User]:
        """Create a new user."""
        user_id = f"{role.value}-{secrets.token_hex(4)}"
        return self.user_manager.create_user(user_id, username, email, password, role)


# Global security manager instance
security_manager = SecurityManager()
