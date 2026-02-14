# models.py

from sqlalchemy.dialects.sqlite import JSON
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import secrets
import random

db = SQLAlchemy()


class Group(db.Model):
    __tablename__ = 'journal_groups'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Back-reference to users in this group
    users = db.relationship('User', backref='group', lazy=True)
    
    # Back-reference to group variables
    group_variables = db.relationship('GroupVariable', back_populates='group', cascade='all, delete-orphan')
    
    # Back-reference to group feature flags
    group_feature_flags = db.relationship('GroupFeatureFlags', back_populates='group', cascade='all, delete-orphan')


class GroupFeatureFlags(db.Model):
    __tablename__ = 'group_feature_flags'
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('journal_groups.id'), nullable=False)
    feature_name = db.Column(db.String(100), nullable=False)
    enabled = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Back-reference to group
    group = db.relationship('Group', back_populates='group_feature_flags')
    
    # Ensure unique combination of group and feature
    __table_args__ = (db.UniqueConstraint('group_id', 'feature_name', name='uq_group_feature'),)


class GroupVariable(db.Model):
    __tablename__ = 'group_variable'
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('journal_groups.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    values = db.Column(JSON, nullable=False, default=list)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Back-reference to group
    group = db.relationship('Group', back_populates='group_variables')
    
    # Back-reference to creator
    creator = db.relationship('User', foreign_keys=[created_by])


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), nullable=False, default='user')
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    has_journal_access = db.Column(db.Boolean, default=False)
    group_id = db.Column(db.Integer, db.ForeignKey('journal_groups.id'), nullable=True)
    country = db.Column(db.String(100), nullable=True)
    phone = db.Column(db.String(50), nullable=True)
    birth_date = db.Column(db.Date, nullable=True)
    reset_token = db.Column(db.String(100), nullable=True)
    reset_token_expires = db.Column(db.DateTime, nullable=True)
    user_source = db.Column(db.String(50), nullable=True)  # 'talaria-prop', 'organic', etc.
    
    # Alias for compatibility with journal backend auth
    @property
    def password(self):
        return self.password_hash
    
    @password.setter
    def password(self, value):
        self.password_hash = value
    
    @property
    def is_admin(self):
        return self.role == 'admin'
    
    @property
    def full_name(self):
        return self.name
    
    @property
    def account_type(self):
        # Return 'admin' for admins, 'group' if in a group, otherwise 'individual'
        if self.role == 'admin':
            return 'admin'
        elif self.group_id:
            return 'group'
        return 'individual'
    
    @property
    def initial_balance(self):
        # Default initial balance - can be customized per user if needed
        return 0.0
    
    @property
    def profile_image(self):
        # Compatibility property - field doesn't exist in this schema
        return None
    
    @property
    def email_verified(self):
        # All migrated users are considered verified
        return True
    
    @property
    def updated_at(self):
        # Return created_at as fallback since updated_at doesn't exist
        return self.created_at

    def get_group_feature_flags(self):
        """Get feature flags for this user's group"""
        if not self.group_id:
            return {}
        
        group_flags = GroupFeatureFlags.query.filter_by(group_id=self.group_id).all()
        return {flag.feature_name: flag.enabled for flag in group_flags}
    
    def generate_verification_token(self):
        """Generate a 6-digit code for password reset"""
        self.reset_token = str(random.randint(100000, 999999))
        self.reset_token_expires = datetime.utcnow() + timedelta(minutes=15)
        return self.reset_token
    
    def verify_reset_token(self, token):
        """Verify the reset token is valid and not expired"""
        if not self.reset_token or not self.reset_token_expires:
            return False
        if self.reset_token != token:
            return False
        if datetime.utcnow() > self.reset_token_expires:
            return False
        return True
    
    def clear_reset_token(self):
        """Clear the reset token after use"""
        self.reset_token = None
        self.reset_token_expires = None

    # Back‐reference so you can do: some_user.import_batches
    import_batches = db.relationship(
        'ImportBatch',
        back_populates='user',
        cascade='all, delete-orphan'
    )

    # Back‐reference so you can do: some_user.journal_entries
    journal_entries = db.relationship(
        'JournalEntry',
        back_populates='user',
        cascade='all, delete-orphan'
    )

    # Back‐reference so you can do: some_user.profiles
    profiles = db.relationship(
        'Profile',
        back_populates='user',
        cascade='all, delete-orphan'
    )

    # Back-reference so you can do: some_user.strategies
    strategies = db.relationship(
        'Strategy',
        back_populates='user',
        cascade='all, delete-orphan'
    )




class Profile(db.Model):
    __tablename__ = 'journal_profiles'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    mode = db.Column(db.String(50), nullable=False, default='journal') # backtest, journal, journal_live
    description = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # FTP settings for 'journal_live' mode
    ftp_host = db.Column(db.String(255), nullable=True)
    ftp_port = db.Column(db.Integer, nullable=True, default=21)
    ftp_username = db.Column(db.String(100), nullable=True)
    ftp_password = db.Column(db.String(255), nullable=True) # Note: Should be encrypted in a real application
    
    # Initial balance for portfolio tracking
    initial_balance = db.Column(db.Numeric(15, 2), default=0)

    # Back‐reference so you can do: some_profile.user
    user = db.relationship('User', back_populates='profiles')

    # Back‐reference so you can do: some_profile.import_batches
    import_batches = db.relationship(
        'ImportBatch',
        back_populates='profile',
        cascade='all, delete-orphan'
    )

    # Back‐reference so you can do: some_profile.journal_entries
    journal_entries = db.relationship(
        'JournalEntry',
        back_populates='profile',
        cascade='all, delete-orphan'
    )




class ImportBatch(db.Model):
    __tablename__ = 'import_batches'

    id = db.Column(db.Integer, primary_key=True)

    # This must match what your routes expect (they do batch = ImportBatch(user_id=…, filename=…, imported_at=…, filepath=…))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    profile_id = db.Column(db.Integer, db.ForeignKey('journal_profiles.id'), nullable=False)
    filename = db.Column(db.String(256), nullable=False)
    imported_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    filepath = db.Column(db.String(512), nullable=False)

    # When you delete a batch, cascade so that its JournalEntry rows go away too
    trades = db.relationship(
        'JournalEntry',
        back_populates='import_batch',
        cascade='all, delete-orphan'
    )

    # Back‐reference so you can do: some_batch.user
    user = db.relationship('User', back_populates='import_batches')
    
    # Back‐reference so you can do: some_batch.profile
    profile = db.relationship('Profile', back_populates='import_batches')


class JournalEntry(db.Model):
    __tablename__ = 'journal_entries'
    id = db.Column(db.Integer, primary_key=True)

    # Every JournalEntry belongs to a user and profile
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    profile_id = db.Column(db.Integer, db.ForeignKey('journal_profiles.id'), nullable=False)

    symbol = db.Column(db.String(20), nullable=False)
    direction = db.Column(db.String(10), nullable=False)
    entry_price = db.Column(db.Float, nullable=False)
    exit_price = db.Column(db.Float, nullable=False)
    stop_loss = db.Column(db.Float, nullable=True)
    take_profit = db.Column(db.Float, nullable=True)
    high_price = db.Column(db.Float, nullable=True)
    low_price = db.Column(db.Float, nullable=True)
    variables = db.Column(JSON, default={})


    quantity = db.Column(db.Float, nullable=False, default=1.0)
    contract_size = db.Column(db.Float, nullable=True, default=None)
    instrument_type = db.Column(db.String(20), nullable=False, default='crypto')
    risk_amount = db.Column(db.Float, nullable=False, default=1.0)

    pnl = db.Column(db.Float, nullable=False, default=0.0)
    strategy = db.Column(db.String(64), nullable=True)
    setup = db.Column(db.String(64), nullable=True)
    rr = db.Column(db.Float, nullable=False, default=0.0)
    notes = db.Column(db.Text, nullable=True)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # New fields for advanced metrics
    commission = db.Column(db.Float, nullable=True)
    slippage = db.Column(db.Float, nullable=True)
    open_time = db.Column(db.DateTime, nullable=True)
    close_time = db.Column(db.DateTime, nullable=True)
    
    # Computed duration fields (populated by database triggers)
    duration_seconds = db.Column(db.Integer, nullable=True)
    duration_minutes = db.Column(db.Integer, nullable=True)
    duration_hours = db.Column(db.Float, nullable=True)
    duration_category = db.Column(db.String(50), nullable=True)
    
    # Screenshot fields
    entry_screenshot = db.Column(db.String(512), nullable=True)
    exit_screenshot = db.Column(db.String(512), nullable=True)

    # If this entry was imported via Excel, store the batch_id
    import_batch_id = db.Column(db.Integer, db.ForeignKey('import_batches.id'), nullable=True)
    import_batch = db.relationship('ImportBatch', back_populates='trades')

    extra_data = db.Column(JSON, default={})

    # Back‐reference so you can do: some_entry.user
    user = db.relationship('User', back_populates='journal_entries')
    
    # Back‐reference so you can do: some_entry.profile
    profile = db.relationship('Profile', back_populates='journal_entries')


class Strategy(db.Model):
    __tablename__ = 'strategies'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    entry_rules = db.Column(JSON, nullable=False, default=list)
    exit_rules = db.Column(JSON, nullable=False, default=list)
    risk_management = db.Column(JSON, nullable=False, default=dict)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Back-reference so you can do: some_strategy.user
    user = db.relationship('User', back_populates='strategies')


class FeatureFlags(db.Model):
    __tablename__ = 'feature_flags'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    enabled = db.Column(db.Boolean, default=True)
    description = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(50), nullable=True)  # core, analytics, advanced, admin, test
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class BlockedIP(db.Model):
    """Tracks blocked IP addresses for application-level security."""
    __tablename__ = 'blocked_ips'
    id = db.Column(db.Integer, primary_key=True)
    ip_address = db.Column(db.String(45), unique=True, nullable=False)  # IPv6 can be up to 45 chars
    reason = db.Column(db.String(255), nullable=False)
    blocked_at = db.Column(db.DateTime, default=datetime.utcnow)
    blocked_until = db.Column(db.DateTime, nullable=True)  # None = permanent
    failed_attempts = db.Column(db.Integer, default=0)
    is_permanent = db.Column(db.Boolean, default=False)
    blocked_by = db.Column(db.String(100), default='system')  # 'system' or admin email
    
    def is_active(self):
        """Check if the block is still active."""
        if self.is_permanent:
            return True
        if self.blocked_until is None:
            return True
        return datetime.utcnow() < self.blocked_until


class SecurityLog(db.Model):
    """Logs security events for monitoring."""
    __tablename__ = 'security_logs'
    id = db.Column(db.Integer, primary_key=True)
    ip_address = db.Column(db.String(45), nullable=False)
    event_type = db.Column(db.String(50), nullable=False)  # failed_login, blocked, suspicious_request, etc.
    details = db.Column(db.Text, nullable=True)
    user_agent = db.Column(db.String(500), nullable=True)
    endpoint = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)


class FailedLoginAttempt(db.Model):
    """Tracks failed login attempts per IP for rate limiting."""
    __tablename__ = 'failed_login_attempts'
    id = db.Column(db.Integer, primary_key=True)
    ip_address = db.Column(db.String(45), nullable=False)
    email_attempted = db.Column(db.String(255), nullable=True)
    attempted_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_agent = db.Column(db.String(500), nullable=True)


class SystemSettings(db.Model):
    """Stores system-wide configuration settings."""
    __tablename__ = 'system_settings'
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text, nullable=False)
    description = db.Column(db.String(255), nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    @classmethod
    def get_setting(cls, key, default=None):
        """Get a setting value by key."""
        setting = cls.query.filter_by(key=key).first()
        return setting.value if setting else default
    
    @classmethod
    def set_setting(cls, key, value, description=None, user_id=None):
        """Set a setting value."""
        setting = cls.query.filter_by(key=key).first()
        if setting:
            setting.value = str(value)
            setting.updated_by = user_id
        else:
            setting = cls(key=key, value=str(value), description=description, updated_by=user_id)
            db.session.add(setting)
        db.session.commit()
        return setting



