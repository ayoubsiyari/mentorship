# routes/admin_routes.py

from flask import Blueprint, request, jsonify, current_app, send_file, make_response
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt, create_access_token, create_refresh_token
from werkzeug.security import generate_password_hash
from models import db, User, Profile, JournalEntry, Group, BlockedIP, SecurityLog, FailedLoginAttempt, SystemSettings
from email_service import mail
from flask_mail import Message
import logging
from datetime import datetime, timedelta
from functools import wraps
import time
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    print("Warning: psutil not available. System metrics will be disabled.")
import os
import csv
import io
import subprocess
import json
import re

admin_bp = Blueprint('admin', __name__)

MIN_JOURNAL_TRADES_FOR_EXPORT = 70


def _safe_excel_sheet_name(name, used_names):
    """Excel sheet names: max 31 chars, no special characters."""
    safe = re.sub(r'[\[\]:*?/\\]', '', str(name or 'User'))[:31]
    if not safe:
        safe = 'User'
    base = safe
    counter = 1
    while safe in used_names:
        suffix = f'_{counter}'
        safe = base[:31 - len(suffix)] + suffix
        counter += 1
    used_names.add(safe)
    return safe


def _journal_entry_to_export_row(entry, user_email='', user_name='', profile_name=''):
    """Build a flat dict for Excel export from a journal entry."""
    entry_datetime = entry.open_time.strftime('%Y-%m-%d %H:%M:%S') if entry.open_time else ''
    exit_datetime = entry.close_time.strftime('%Y-%m-%d %H:%M:%S') if entry.close_time else ''
    created_at = entry.created_at.strftime('%Y-%m-%d %H:%M:%S') if entry.created_at else ''
    updated_at = entry.updated_at.strftime('%Y-%m-%d %H:%M:%S') if entry.updated_at else ''
    trade_date = entry.date.strftime('%Y-%m-%d %H:%M:%S') if entry.date else ''

    variables_str = ''
    if entry.variables:
        try:
            variables_str = json.dumps(entry.variables)
        except Exception:
            variables_str = str(entry.variables)

    extra_data_str = ''
    if entry.extra_data:
        try:
            extra_data_str = json.dumps(entry.extra_data)
        except Exception:
            extra_data_str = str(entry.extra_data)

    var1 = entry.extra_data.get('var1', '') if entry.extra_data else ''
    var2 = entry.extra_data.get('var2', '') if entry.extra_data else ''
    var3 = entry.extra_data.get('var3', '') if entry.extra_data else ''
    var4 = entry.extra_data.get('var4', '') if entry.extra_data else ''
    var5 = entry.extra_data.get('var5', '') if entry.extra_data else ''
    var6 = entry.extra_data.get('var6', '') if entry.extra_data else ''
    var7 = entry.extra_data.get('var7', '') if entry.extra_data else ''
    var8 = entry.extra_data.get('var8', '') if entry.extra_data else ''
    var9 = entry.extra_data.get('var9', '') if entry.extra_data else ''
    var10 = entry.extra_data.get('var10', '') if entry.extra_data else ''

    setup = ''
    strategy_var = ''
    if entry.variables:
        setup = ', '.join(entry.variables.get('setup', [])) if entry.variables.get('setup') else ''
        strategy_var = ', '.join(entry.variables.get('strategy', [])) if entry.variables.get('strategy') else ''

    return {
        'user_email': user_email,
        'user_name': user_name,
        'profile_name': profile_name,
        'symbol': entry.symbol,
        'direction': entry.direction,
        'entry_price': entry.entry_price,
        'exit_price': entry.exit_price,
        'stop_loss': entry.stop_loss,
        'take_profit': entry.take_profit,
        'high_price': entry.high_price,
        'low_price': entry.low_price,
        'quantity': entry.quantity,
        'contract_size': entry.contract_size,
        'instrument_type': entry.instrument_type,
        'risk_amount': entry.risk_amount,
        'pnl': entry.pnl,
        'rr': entry.rr,
        'strategy': entry.strategy or strategy_var,
        'setup': entry.setup or setup,
        'notes': entry.notes,
        'entry_datetime': entry_datetime,
        'exit_datetime': exit_datetime,
        'trade_date': trade_date,
        'created_at': created_at,
        'updated_at': updated_at,
        'duration_seconds': entry.duration_seconds,
        'duration_minutes': entry.duration_minutes,
        'duration_hours': entry.duration_hours,
        'duration_category': entry.duration_category,
        'commission': entry.commission,
        'slippage': entry.slippage,
        'entry_screenshot': entry.entry_screenshot,
        'exit_screenshot': entry.exit_screenshot,
        'var1': var1,
        'var2': var2,
        'var3': var3,
        'var4': var4,
        'var5': var5,
        'var6': var6,
        'var7': var7,
        'var8': var8,
        'var9': var9,
        'var10': var10,
        'variables_json': variables_str,
        'extra_data_json': extra_data_str,
        'id': entry.id,
        'import_batch_id': entry.import_batch_id,
    }

# Setup logging for admin actions
admin_logger = logging.getLogger('admin_actions')
admin_logger.setLevel(logging.INFO)

# Rate limiting for admin endpoints
admin_requests = {}

# Store recent activity for the dashboard
recent_activities = []

def rate_limit_admin(max_requests=10, window_seconds=60):
    """Rate limiting decorator for admin endpoints"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_id = get_jwt_identity()
            current_time = time.time()
            
            # Clean old entries
            admin_requests.clear()
            for key, timestamp in list(admin_requests.items()):
                if current_time - timestamp > window_seconds:
                    del admin_requests[key]
            
            # Check rate limit
            request_key = f"{user_id}_{f.__name__}"
            if request_key in admin_requests:
                return jsonify({"error": "Rate limit exceeded. Please wait before making another request."}), 429
            
            admin_requests[request_key] = current_time
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def is_admin_user():
    """
    Return True if the current JWT has is_admin=True.
    """
    claims = get_jwt()
    return claims.get('is_admin', False)
def admin_required(f):
    """
    Decorator to require admin access for endpoints
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_admin_user():
            return jsonify({"error": "Admin access required"}), 403
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """
    Decorator to require admin access for endpoints
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_admin_user():
            return jsonify({"error": "Admin access required"}), 403
        return f(*args, **kwargs)
    return decorated_function

def log_admin_action(action, details=""):
    """Log admin actions for security audit"""
    user_id = get_jwt_identity()
    timestamp = datetime.now().isoformat()
    log_entry = f"{timestamp} - User {user_id} - {action} - {details}"
    admin_logger.info(log_entry)
    
    # Store in recent activities for dashboard
    activity = {
        "action": action,
        "details": details,
        "user_id": user_id,
        "timestamp": timestamp
    }
    recent_activities.append(activity)
    
    # Keep only last 100 activities
    if len(recent_activities) > 100:
        recent_activities.pop(0)

@admin_bp.route('/dashboard', methods=['GET'])
@jwt_required()
@rate_limit_admin(max_requests=20, window_seconds=60)
def admin_dashboard():
    """
    Admin-only: Get comprehensive dashboard statistics.
    """
    if not is_admin_user():
        return jsonify({"error": "Only admins can access dashboard"}), 403

    try:
        # Get basic statistics
        total_users = User.query.count()
        total_profiles = Profile.query.count()
        total_trades = JournalEntry.query.count()
        total_journals = JournalEntry.query.count()
        
        # Get recent activity
        recent_users = User.query.order_by(User.id.desc()).limit(5).all()
        recent_trades = JournalEntry.query.order_by(JournalEntry.id.desc()).limit(10).all()
        
        # Get admin users
        admin_users = User.query.filter_by(is_admin=True).all()
        
        # Calculate some metrics
        active_users_30d = User.query.filter(
            User.created_at >= datetime.now() - timedelta(days=30)
        ).count()
        
        # Mask sensitive data
        masked_users = []
        for user in recent_users:
            email = user.email
            if email and '@' in email:
                parts = email.split('@')
                masked_email = f"{parts[0][:2]}***@{parts[1]}"
            else:
                masked_email = "***"
            
            masked_users.append({
                "id": user.id,
                "email": masked_email,
                "is_admin": user.is_admin,
                "created_at": user.created_at.isoformat() if user.created_at else None
            })
        
        masked_trades = []
        for trade in recent_trades:
            masked_trades.append({
                "id": trade.id,
                "symbol": trade.symbol,
                "entry_price": trade.entry_price,
                "exit_price": trade.exit_price,
                "pnl": trade.pnl,
                "created_at": trade.created_at.isoformat() if trade.created_at else None
            })
        
        dashboard_data = {
            "statistics": {
                "total_users": total_users,
                "total_profiles": total_profiles,
                "total_trades": total_trades,
                "total_journals": total_journals,
                "active_users_30d": active_users_30d,
                "admin_users_count": len(admin_users)
            },
            "recent_users": masked_users,
            "recent_trades": masked_trades,
            "admin_users": [
                {
                    "id": user.id,
                    "email": user.email[:2] + "***@" + user.email.split('@')[1] if '@' in user.email else "***",
                    "created_at": user.created_at.isoformat() if user.created_at else None
                }
                for user in admin_users
            ]
        }
        
        log_admin_action("VIEW_DASHBOARD", f"Viewed dashboard with {total_users} users")
        return jsonify(dashboard_data), 200
        
    except Exception as e:
        current_app.logger.error(f"Error in admin dashboard: {e}")
        return jsonify({"error": "Internal server error"}), 500

@admin_bp.route('/users', methods=['GET'])
@jwt_required()
@rate_limit_admin(max_requests=15, window_seconds=60)
def list_users():
    """
    Admin-only: List all users with pagination and filtering.
    Query params: page (default 1), per_page (default 20), search (optional)
    """
    if not is_admin_user():
        return jsonify({"error": "Only admins can view users"}), 403

    try:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 10000)  # Max 10000 per page
        search = request.args.get('search', '').strip()
        
        query = User.query
        
        if search:
            query = query.filter(User.email.ilike(f'%{search}%'))
        
        pagination = query.order_by(User.id.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )

        user_ids = [user.id for user in pagination.items]
        profile_counts = {}
        trade_counts = {}
        if user_ids:
            from sqlalchemy import func
            profile_counts = dict(
                db.session.query(Profile.user_id, func.count(Profile.id))
                .filter(Profile.user_id.in_(user_ids))
                .group_by(Profile.user_id)
                .all()
            )
            trade_counts = dict(
                db.session.query(JournalEntry.user_id, func.count(JournalEntry.id))
                .filter(JournalEntry.user_id.in_(user_ids))
                .group_by(JournalEntry.user_id)
                .all()
            )
        
        users = []
        for user in pagination.items:
            journals_count = profile_counts.get(user.id, 0)
            trades_count = trade_counts.get(user.id, 0)
            # Return complete user information for admin interface
            users.append({
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "phone": user.phone,
                "country": user.country,
                "profile_image": user.profile_image,
                "is_admin": user.is_admin,
                "email_verified": user.email_verified,
                "has_journal_access": user.has_journal_access,
                "user_source": user.user_source,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "updated_at": user.updated_at.isoformat() if user.updated_at else None,
                # Additional computed fields
                "profiles_count": journals_count,
                "journals_count": journals_count,
                "trades_count": trades_count,
                "last_activity": user.updated_at.isoformat() if user.updated_at else None
            })
        
        result = {
            "users": users,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": pagination.total,
                "pages": pagination.pages,
                "has_next": pagination.has_next,
                "has_prev": pagination.has_prev
            }
        }
        
        log_admin_action("LIST_USERS", f"Listed {len(users)} users, page {page}")
        return jsonify(result), 200
        
    except Exception as e:
        current_app.logger.error(f"Error listing users: {e}")
        return jsonify({"error": "Internal server error"}), 500

@admin_bp.route('/users/<int:user_id>', methods=['GET'])
@jwt_required()
@rate_limit_admin(max_requests=20, window_seconds=60)
def get_user_details(user_id):
    """
    Admin-only: Get detailed user information by ID.
    """
    if not is_admin_user():
        return jsonify({"error": "Only admins can view user details"}), 403

    try:
        user = User.query.get_or_404(user_id)
        
        # Get user's profiles and trades
        profiles = Profile.query.filter_by(user_id=user_id).all()
        trades = JournalEntry.query.filter_by(user_id=user_id).order_by(JournalEntry.id.desc()).limit(10).all()
        journals = JournalEntry.query.filter_by(user_id=user_id).order_by(JournalEntry.id.desc()).limit(5).all()
        
        user_data = {
            "id": user.id,
            "email": user.email,  # Full email for admin view
            "full_name": user.full_name,
            "phone": user.phone,
            "country": user.country,
            "profile_image": user.profile_image,
            "is_admin": user.is_admin,
            "email_verified": user.email_verified,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "updated_at": user.updated_at.isoformat() if user.updated_at else None,
            "profiles_count": len(profiles),
            "trades_count": JournalEntry.query.filter_by(user_id=user_id).count(),
            "journals_count": len(profiles),
            "profiles": [
                {
                    "id": profile.id,
                    "name": profile.name,
                    "description": profile.description,
                    "is_active": profile.is_active,
                    "created_at": profile.created_at.isoformat() if profile.created_at else None
                }
                for profile in profiles
            ],
            "recent_trades": [
                {
                    "id": trade.id,
                    "symbol": trade.symbol,
                    "direction": trade.direction,
                    "entry_price": trade.entry_price,
                    "exit_price": trade.exit_price,
                    "pnl": trade.pnl,
                    "strategy": trade.strategy,
                    "setup": trade.setup,
                    "date": trade.date.isoformat() if trade.date else None,
                    "created_at": trade.created_at.isoformat() if trade.created_at else None
                }
                for trade in trades
            ]
        }
        
        log_admin_action("VIEW_USER_DETAILS", f"Viewed details for user {user_id}")
        return jsonify(user_data), 200
        
    except Exception as e:
        current_app.logger.error(f"Error getting user details: {e}")
        return jsonify({"error": "Internal server error"}), 500

@admin_bp.route('/users', methods=['POST'])
@jwt_required()
@rate_limit_admin(max_requests=5, window_seconds=60)
def create_user():
    """
    Admin-only: Create a new user.
    Expect JSON: { email, password, is_admin (boolean) }
    """
    if not is_admin_user():
        return jsonify({"error": "Only admins can create users"}), 403

    try:
        data = request.get_json() or {}
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        full_name = data.get('full_name', '').strip()
        phone = data.get('phone', '').strip()
        country = data.get('country', '').strip()
        profile_image = data.get('profile_image', '').strip()
        is_admin_flag = bool(data.get('is_admin', False))

        if not email or not password:
            return jsonify({"error": "Must include email and password"}), 400

        # Validate email format
        if '@' not in email or '.' not in email:
            return jsonify({"error": "Invalid email format"}), 400

        # Validate password strength
        if len(password) < 8:
            return jsonify({"error": "Password must be at least 8 characters long"}), 400

        if User.query.filter_by(email=email).first():
            return jsonify({"error": "Email already in use"}), 400

        hashed_pw = generate_password_hash(password)
        new_user = User()
        new_user.email = email
        new_user.password = hashed_pw
        new_user.full_name = full_name if full_name else None
        new_user.phone = phone if phone else None
        new_user.country = country if country else None
        new_user.profile_image = profile_image if profile_image else None
        new_user.is_admin = is_admin_flag
        db.session.add(new_user)
        db.session.commit() 

        log_admin_action("CREATE_USER", f"Created user {email} (admin: {is_admin_flag})")
        
        return jsonify({
            "message": "User created successfully",
            "user": {
                "id": new_user.id,
                "email": new_user.email,
                "full_name": new_user.full_name,
                "phone": new_user.phone,
                "country": new_user.country,
                "profile_image": new_user.profile_image,
                "is_admin": new_user.is_admin,
                "email_verified": new_user.email_verified,
                "created_at": new_user.created_at.isoformat() if new_user.created_at else None
            }
        }), 201
        
    except Exception as e:
        current_app.logger.error(f"Error creating user: {e}")
        db.session.rollback()
        return jsonify({"error": "Internal server error"}), 500

@admin_bp.route('/users/<int:user_id>', methods=['PUT'])
@jwt_required()
@rate_limit_admin(max_requests=10, window_seconds=60)
def update_user(user_id):
    """
    Admin-only: Update user information.
    Expect JSON: { email (optional), is_admin (optional) }
    """
    if not is_admin_user():
        return jsonify({"error": "Only admins can update users"}), 403

    try:
        user = User.query.get_or_404(user_id)
        data = request.get_json() or {}
        
        if 'email' in data:
            new_email = data['email'].strip().lower()
            if '@' not in new_email or '.' not in new_email:
                return jsonify({"error": "Invalid email format"}), 400
            
            # Check if email is already taken by another user
            existing_user = User.query.filter_by(email=new_email).first()
            if existing_user and existing_user.id != user_id:
                return jsonify({"error": "Email already in use"}), 400
            
            user.email = new_email
        
        if 'is_admin' in data:
            user.is_admin = bool(data['is_admin'])
        if 'email_verified' in data:
            user.email_verified = bool(data['email_verified'])
        
        db.session.commit()
        
        log_admin_action("UPDATE_USER", f"Updated user {user_id}")
        
        return jsonify({
            "message": "User updated successfully",
            "user": {
                "id": user.id,
                "email": user.email,
                "is_admin": user.is_admin
            }
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error updating user: {e}")
        db.session.rollback()
        return jsonify({"error": "Internal server error"}), 500

@admin_bp.route('/users/<int:user_id>', methods=['DELETE'])
@jwt_required()
@rate_limit_admin(max_requests=3, window_seconds=60)
def delete_user(user_id):
    """
    Admin-only: Delete an existing user by ID.
    """
    if not is_admin_user():
        return jsonify({"error": "Only admins can delete users"}), 403

    try:
        user = User.query.get_or_404(user_id)
        user_email = user.email
        
        # Prevent admin from deleting themselves
        current_user_id = int(get_jwt_identity())
        if user_id == current_user_id:
            return jsonify({"error": "Cannot delete your own account"}), 400
        
        db.session.delete(user)
        db.session.commit()
        
        log_admin_action("DELETE_USER", f"Deleted user {user_id} ({user_email})")
        
        return jsonify({"message": f"User {user_email} deleted successfully"}), 200
        
    except Exception as e:
        current_app.logger.error(f"Error deleting user: {e}")
        db.session.rollback()
        return jsonify({"error": "Internal server error"}), 500

@admin_bp.route('/logs', methods=['GET'])
@jwt_required()
@rate_limit_admin(max_requests=10, window_seconds=60)
def get_admin_logs():
    """
    Admin-only: Get recent admin action logs.
    Query params: limit (default 50, max 100)
    """
    if not is_admin_user():
        return jsonify({"error": "Only admins can view logs"}), 403

    try:
        limit = min(request.args.get('limit', 50, type=int), 100)
        
        logs = []
        
        # Try to read from admin_access.log file
        try:
            with open('admin_access.log', 'r') as f:
                lines = f.readlines()
                for line in reversed(lines[-limit:]):
                    line = line.strip()
                    if line:
                        # Parse log line: "2024-01-01 12:00:00 - ACTION_TYPE - details"
                        parts = line.split(' - ', 2)
                        if len(parts) >= 2:
                            logs.append({
                                "timestamp": parts[0],
                                "action": parts[1] if len(parts) > 1 else "LOG",
                                "details": parts[2] if len(parts) > 2 else line
                            })
                        else:
                            logs.append({
                                "timestamp": datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
                                "action": "LOG",
                                "details": line
                            })
        except FileNotFoundError:
            pass
        
        # Also get security logs from database
        try:
            security_logs = SecurityLog.query.order_by(SecurityLog.created_at.desc()).limit(limit).all()
            for log in security_logs:
                logs.append({
                    "timestamp": log.created_at.strftime('%Y-%m-%d %H:%M:%S') if log.created_at else 'N/A',
                    "action": log.event_type.upper() if log.event_type else 'SECURITY',
                    "details": f"IP: {log.ip_address} - {log.details}" if log.details else f"IP: {log.ip_address}"
                })
        except Exception as e:
            current_app.logger.error(f"Error fetching security logs: {e}")
        
        # Sort by timestamp descending
        logs.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        logs = logs[:limit]
        
        log_admin_action("VIEW_LOGS", f"Viewed {len(logs)} log entries")
        
        return jsonify({
            "logs": logs,
            "count": len(logs)
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error getting admin logs: {e}")
        return jsonify({"error": "Internal server error"}), 500

@admin_bp.route('/system/health', methods=['GET'])
@jwt_required()
@rate_limit_admin(max_requests=30, window_seconds=60)
def system_health():
    """
    Admin-only: Get system health information.
    """
    if not is_admin_user():
        return jsonify({"error": "Only admins can view system health"}), 403

    try:
        # Test database connection
        db_status = "healthy"
        try:
            db.session.execute(db.text("SELECT 1"))
        except Exception as e:
            db_status = f"error: {str(e)}"
        
        # Get basic system info
        health_data = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "database": {
                "status": db_status,
                "total_users": User.query.count(),
                "total_trades": JournalEntry.query.count()
            },
            "environment": current_app.config.get('ENV', 'development'),
            "debug_mode": current_app.config.get('DEBUG', False)
        }
        
        log_admin_action("VIEW_SYSTEM_HEALTH", f"System health check - DB: {db_status}")
        
        return jsonify(health_data), 200
        
    except Exception as e:
        current_app.logger.error(f"Error in system health check: {e}")
        return jsonify({"error": "Internal server error"}), 500

@admin_bp.route('/system/metrics', methods=['GET'])
@jwt_required()
@rate_limit_admin(max_requests=30, window_seconds=60)
def system_metrics():
    """
    Admin-only: Get detailed system metrics including CPU, memory, disk usage.
    """
    if not is_admin_user():
        return jsonify({"error": "Only admins can view system metrics"}), 403

    try:
        if PSUTIL_AVAILABLE:
            # Get system metrics using psutil
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Get system uptime
            uptime_seconds = time.time() - psutil.boot_time()
            uptime_hours = uptime_seconds / 3600
            
            # Get load average (Linux only)
            try:
                load_avg = psutil.getloadavg()
            except:
                load_avg = [0, 0, 0]
            
            metrics_data = {
                "cpu": {
                    "percent": cpu_percent,
                    "count": psutil.cpu_count()
                },
                "memory": {
                    "total": memory.total,
                    "available": memory.available,
                    "percent": memory.percent,
                    "used": memory.used
                },
                "disk": {
                    "total": disk.total,
                    "used": disk.used,
                    "free": disk.free,
                    "percent": (disk.used / disk.total) * 100
                },
                "uptime": {
                    "seconds": uptime_seconds,
                    "hours": uptime_hours,
                    "formatted": f"{int(uptime_hours)}h {int((uptime_hours % 1) * 60)}m"
                },
                "load_average": load_avg,
                "timestamp": datetime.now().isoformat()
            }
        else:
            # Fallback when psutil is not available
            metrics_data = {
                "cpu": {
                    "percent": 0,
                    "count": 0
                },
                "memory": {
                    "total": 0,
                    "available": 0,
                    "percent": 0,
                    "used": 0
                },
                "disk": {
                    "total": 0,
                    "used": 0,
                    "free": 0,
                    "percent": 0
                },
                "uptime": {
                    "seconds": 0,
                    "hours": 0,
                    "formatted": "N/A"
                },
                "load_average": [0, 0, 0],
                "timestamp": datetime.now().isoformat(),
                "note": "System metrics disabled - psutil not available"
            }
        
        if PSUTIL_AVAILABLE:
            log_admin_action("VIEW_SYSTEM_METRICS", f"System metrics - CPU: {cpu_percent}%, Memory: {memory.percent}%")
        else:
            log_admin_action("VIEW_SYSTEM_METRICS", "System metrics disabled - psutil not available")
        
        return jsonify(metrics_data), 200
        
    except Exception as e:
        current_app.logger.error(f"Error getting system metrics: {e}")
        return jsonify({"error": "Internal server error"}), 500

@admin_bp.route('/activity', methods=['GET'])
@jwt_required()
@rate_limit_admin(max_requests=20, window_seconds=60)
def get_recent_activity():
    """
    Admin-only: Get recent admin activities for the dashboard.
    Query params: limit (default 10, max 50)
    """
    if not is_admin_user():
        return jsonify({"error": "Only admins can view activity"}), 403

    try:
        limit = min(request.args.get('limit', 10, type=int), 50)
        
        # Get recent activities
        activities = recent_activities[-limit:] if recent_activities else []
        
        # Format activities for frontend
        formatted_activities = []
        for activity in activities:
            # Get user email for display
            user = User.query.get(activity['user_id'])
            user_email = user.email if user else f"User {activity['user_id']}"
            
            formatted_activities.append({
                "action": activity['action'],
                "details": activity['details'],
                "user": user_email,
                "timestamp": activity['timestamp']
            })
        
        log_admin_action("VIEW_ACTIVITY", f"Viewed {len(formatted_activities)} activities")
        
        return jsonify({
            "activities": formatted_activities,
            "count": len(formatted_activities)
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error getting recent activity: {e}")
        return jsonify({"error": "Internal server error"}), 500

@admin_bp.route('/users/bulk', methods=['POST'])
@jwt_required()
@rate_limit_admin(max_requests=5, window_seconds=60)
def bulk_user_operations():
    """
    Admin-only: Perform bulk operations on users.
    Expect JSON: { action: "delete"|"activate"|"deactivate", user_ids: [1,2,3] }
    """
    if not is_admin_user():
        return jsonify({"error": "Only admins can perform bulk operations"}), 403

    try:
        data = request.get_json() or {}
        action = data.get('action')
        user_ids = data.get('user_ids', [])
        
        if not action or not user_ids:
            return jsonify({"error": "Must provide action and user_ids"}), 400
        
        if action not in ['delete', 'activate', 'deactivate']:
            return jsonify({"error": "Invalid action. Must be delete, activate, or deactivate"}), 400
        
        current_user_id = int(get_jwt_identity())
        affected_users = []
        
        for user_id in user_ids:
            if user_id == current_user_id:
                continue  # Skip current user
                
            user = User.query.get(user_id)
            if not user:
                continue
                
            if action == 'delete':
                db.session.delete(user)
                affected_users.append(user.email)
            elif action == 'activate':
                user.email_verified = True
                affected_users.append(user.email)
            elif action == 'deactivate':
                user.email_verified = False
                affected_users.append(user.email)
        
        db.session.commit()
        
        log_admin_action(f"BULK_{action.upper()}", f"Bulk {action} on {len(affected_users)} users")
        
        return jsonify({
            "message": f"Bulk {action} completed successfully",
            "affected_users": affected_users,
            "count": len(affected_users)
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error in bulk user operations: {e}")
        db.session.rollback()
        return jsonify({"error": "Internal server error"}), 500

@admin_bp.route('/users/export', methods=['GET'])
@jwt_required()
@rate_limit_admin(max_requests=5, window_seconds=60)
def export_users():
    """
    Admin-only: Export users data in CSV format.
    Query params: format (default 'csv')
    """
    if not is_admin_user():
        return jsonify({"error": "Only admins can export users"}), 403

    try:
        export_format = request.args.get('format', 'csv').lower()
        
        if export_format != 'csv':
            return jsonify({"error": "Only CSV format is supported"}), 400
        
        # Get all users
        users = User.query.all()
        
        # Create CSV data
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(['ID', 'Email', 'Full Name', 'Phone', 'Country', 'Profile Image', 'Is Admin', 'Email Verified', 'Profiles Count', 'Trades Count', 'Created At', 'Updated At'])
        
        # Write user data
        for user in users:
            writer.writerow([
                user.id,
                user.email,
                user.full_name or '',
                user.phone or '',
                user.country or '',
                user.profile_image or '',
                user.is_admin,
                user.email_verified,
                len(user.profiles),
                len(user.journal_entries),
                user.created_at.isoformat() if user.created_at else '',
                user.updated_at.isoformat() if user.updated_at else ''
            ])
        
        output.seek(0)
        
        log_admin_action("EXPORT_USERS", f"Exported {len(users)} users to CSV")
        
        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8')),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'users-export-{datetime.now().strftime("%Y%m%d-%H%M%S")}.csv'
        )
        
    except Exception as e:
        current_app.logger.error(f"Error exporting users: {e}")
        return jsonify({"error": "Internal server error"}), 500


@admin_bp.route('/users/export-journals', methods=['POST'])
@jwt_required()
@rate_limit_admin(max_requests=5, window_seconds=120)
def export_user_journals():
    """
    Admin-only: Export journal trades for selected users.
    Only users with more than min_trades (default 70) are included.
    Expects JSON: { user_ids: [...], min_trades: 70 }
    """
    if not is_admin_user():
        return jsonify({"error": "Only admins can export journals"}), 403

    try:
        import pandas as pd

        data = request.get_json() or {}
        user_ids = data.get('user_ids', [])
        min_trades = int(data.get('min_trades', MIN_JOURNAL_TRADES_FOR_EXPORT))

        if not user_ids:
            return jsonify({"error": "No users selected"}), 400

        qualifying_users = []
        skipped_users = []

        for user_id in user_ids:
            user = User.query.get(user_id)
            if not user:
                skipped_users.append({
                    "id": user_id,
                    "email": "",
                    "trades_count": 0,
                    "reason": "User not found"
                })
                continue

            trade_count = JournalEntry.query.filter_by(user_id=user_id).count()
            if trade_count <= min_trades:
                skipped_users.append({
                    "id": user.id,
                    "email": user.email,
                    "trades_count": trade_count,
                    "reason": f"Only {trade_count} trades (requires more than {min_trades})"
                })
                continue

            qualifying_users.append((user, trade_count))

        if not qualifying_users:
            return jsonify({
                "error": f"No selected users have more than {min_trades} trades",
                "skipped": skipped_users
            }), 400

        output = io.BytesIO()
        used_sheet_names = set()

        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            summary_rows = []
            for user, trade_count in qualifying_users:
                summary_rows.append({
                    "status": "exported",
                    "email": user.email,
                    "name": user.full_name or "",
                    "trades_count": trade_count
                })
            for skipped in skipped_users:
                summary_rows.append({
                    "status": "skipped",
                    "email": skipped.get("email", ""),
                    "name": "",
                    "trades_count": skipped.get("trades_count", 0),
                    "reason": skipped.get("reason", "")
                })
            pd.DataFrame(summary_rows).to_excel(writer, index=False, sheet_name='Summary')
            used_sheet_names.add('Summary')

            for user, _ in qualifying_users:
                entries = JournalEntry.query.filter_by(user_id=user.id).order_by(JournalEntry.date.asc()).all()
                profile_names = {
                    p.id: p.name for p in Profile.query.filter_by(user_id=user.id).all()
                }
                rows = [
                    _journal_entry_to_export_row(
                        entry,
                        user_email=user.email,
                        user_name=user.full_name or '',
                        profile_name=profile_names.get(entry.profile_id, '')
                    )
                    for entry in entries
                ]
                sheet_name = _safe_excel_sheet_name(user.email.split('@')[0], used_sheet_names)
                pd.DataFrame(rows).to_excel(writer, index=False, sheet_name=sheet_name)

        output.seek(0)

        log_admin_action(
            "EXPORT_USER_JOURNALS",
            f"Exported journals for {len(qualifying_users)} users (min_trades>{min_trades}), skipped {len(skipped_users)}"
        )

        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'user-journals-export-{datetime.now().strftime("%Y%m%d-%H%M%S")}.xlsx'
        )

    except Exception as e:
        current_app.logger.error(f"Error exporting user journals: {e}")
        return jsonify({"error": "Internal server error"}), 500

# Enhanced dashboard endpoint with more comprehensive data
@admin_bp.route('/dashboard/enhanced', methods=['GET'])
@jwt_required()
@rate_limit_admin(max_requests=20, window_seconds=60)
def enhanced_dashboard():
    """
    Admin-only: Get enhanced dashboard with more detailed statistics.
    """
    if not is_admin_user():
        return jsonify({"error": "Only admins can access enhanced dashboard"}), 403

    try:
        # Get comprehensive statistics
        total_users = User.query.count()
        active_users_30d = User.query.filter(
            User.created_at >= datetime.now() - timedelta(days=30)
        ).count()
        total_trades = JournalEntry.query.count()
        admin_users = User.query.filter_by(is_admin=True).count()
        
        # Get recent statistics
        users_today = User.query.filter(
            User.created_at >= datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        ).count()
        
        trades_today = JournalEntry.query.filter(
            JournalEntry.created_at >= datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        ).count()
        
        # Calculate growth rates
        users_last_week = User.query.filter(
            User.created_at >= datetime.now() - timedelta(days=7)
        ).count()
        
        users_last_month = User.query.filter(
            User.created_at >= datetime.now() - timedelta(days=30)
        ).count()
        
        # Get system metrics
        if PSUTIL_AVAILABLE:
            try:
                cpu_percent = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()
                disk = psutil.disk_usage('/')
            except:
                cpu_percent = 0
                memory = type('obj', (object,), {'percent': 0})()
                disk = type('obj', (object,), {'percent': 0})()
        else:
            cpu_percent = 0
            memory = type('obj', (object,), {'percent': 0})()
            disk = type('obj', (object,), {'percent': 0})()
        
        enhanced_data = {
            "total_users": total_users,
            "active_users": active_users_30d,
            "total_trades": total_trades,
            "admin_users": admin_users,
            "users_today": users_today,
            "trades_today": trades_today,
            "growth": {
                "users_this_week": users_last_week,
                "users_this_month": users_last_month,
                "weekly_growth": round(((users_last_week - (users_last_month - users_last_week)) / max(users_last_month - users_last_week, 1)) * 100, 1)
            },
            "system": {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "disk_percent": (disk.used / disk.total) * 100 if hasattr(disk, 'total') and disk.total > 0 else 0,
                "uptime": time.time() - psutil.boot_time()
            },
            "recent_activity": recent_activities[-5:] if recent_activities else []
        }
        
        log_admin_action("VIEW_ENHANCED_DASHBOARD", f"Enhanced dashboard - {total_users} users, {total_trades} trades")
        
        return jsonify(enhanced_data), 200
        
    except Exception as e:
        current_app.logger.error(f"Error in enhanced dashboard: {e}")
        return jsonify({"error": "Internal server error"}), 500


# ─── BULK USER IMPORT ──────────────────────────────────────────────────────

@admin_bp.route('/import-users', methods=['POST'])
@jwt_required()
@admin_required
@rate_limit_admin(max_requests=3, window_seconds=300)  # 3 imports per 5 minutes
def import_bulk_users():
    """
    Import multiple users from CSV/Excel file
    Expected format: email,password,full_name,phone,country,is_admin,group_name,account_type
    
    Account Types:
    - individual: Regular student accounts (sees only their own data)
    - group: Group accounts (sees ALL data from group members)  
    - admin: Admin accounts (full access)
    
    Group System:
    - Students log in individually: student1-group1@school.com
    - Group account sees ALL student data: group1@school.com
    - No conflicts, no crashes!
    """
    try:
        # Check if file is present
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Validate file type
        allowed_extensions = {'.csv', '.xlsx', '.xls'}
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in allowed_extensions:
            return jsonify({'error': 'Only CSV and Excel files are allowed'}), 400
        
        imported_count = 0
        errors = []
        skipped_count = 0
        
        try:
            if file_ext == '.csv':
                # Read CSV file
                stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
                csv_input = csv.DictReader(stream)
                rows = list(csv_input)
            else:
                # Read Excel file
                import pandas as pd
                df = pd.read_excel(file)
                rows = df.to_dict('records')
            
            # Process each row
            for row_num, row in enumerate(rows, start=2):  # Start at 2 because row 1 is header
                try:
                    # Extract and validate data
                    email = str(row.get('email', '')).strip().lower()
                    password = str(row.get('password', '')).strip()
                    full_name = str(row.get('full_name', '')).strip()
                    phone = str(row.get('phone', '')).strip()
                    country = str(row.get('country', '')).strip()
                    is_admin = str(row.get('is_admin', 'false')).strip().lower() in ['true', '1', 'yes']
                    group_name = str(row.get('group_name', '')).strip()
                    account_type = str(row.get('account_type', 'individual')).strip().lower()
                    
                    # Validate account_type
                    if account_type not in ['individual', 'group', 'admin']:
                        account_type = 'individual'
                    
                    # Validate required fields
                    if not email or not password:
                        errors.append(f"Row {row_num}: Email and password are required")
                        continue
                    
                    # Check if user already exists
                    existing_user = User.query.filter_by(email=email).first()
                    if existing_user:
                        skipped_count += 1
                        errors.append(f"Row {row_num}: User {email} already exists - skipped")
                        continue
                    
                    # Validate email format
                    if '@' not in email or '.' not in email:
                        errors.append(f"Row {row_num}: Invalid email format: {email}")
                        continue
                    
                    # Validate password strength
                    if len(password) < 8:
                        errors.append(f"Row {row_num}: Password must be at least 8 characters")
                        continue
                    
                    # Handle group assignment
                    group_id = None
                    if group_name:
                        # Find or create group
                        group = Group.query.filter_by(name=group_name).first()
                        if not group:
                            group = Group(name=group_name, description=f"Auto-created group: {group_name}")
                            db.session.add(group)
                            db.session.flush()  # Get the group ID
                        group_id = group.id
                    
                    # Create new user
                    hashed_password = generate_password_hash(password)
                    
                    new_user = User(
                        email=email,
                        password=hashed_password,
                        full_name=full_name if full_name else None,
                        phone=phone if phone else None,
                        country=country if country else None,
                        is_admin=is_admin,
                        email_verified=True,  # Auto-verify imported users
                        group_id=group_id,  # Assign to group
                        account_type=account_type  # Set account type
                    )
                    
                    db.session.add(new_user)
                    db.session.flush()  # Get the user ID
                    
                    # Create default profile for the user
                    default_profile = Profile(
                        user_id=new_user.id,
                        name="Default Profile",
                        description="Default trading profile",
                        is_active=True
                    )
                    db.session.add(default_profile)
                    
                    imported_count += 1
                    
                except Exception as row_error:
                    errors.append(f"Row {row_num}: {str(row_error)}")
                    continue
            
            # Commit all changes
            db.session.commit()
            
            # Log the import activity
            activity = {
                "action": "bulk_user_import",
                "user": get_jwt_identity(),
                "timestamp": datetime.utcnow().isoformat(),
                "details": f"Imported {imported_count} users, skipped {skipped_count}, {len(errors)} errors",
                "imported_count": imported_count,
                "skipped_count": skipped_count,
                "error_count": len(errors)
            }
            recent_activities.insert(0, activity)
            if len(recent_activities) > 100:
                recent_activities.pop()
            
            return jsonify({
                'success': True,
                'message': f'Import completed successfully',
                'imported_count': imported_count,
                'skipped_count': skipped_count,
                'error_count': len(errors),
                'errors': errors[:10] if errors else []  # Return first 10 errors
            }), 200
            
        except Exception as parse_error:
            return jsonify({'error': f'Error parsing file: {str(parse_error)}'}), 400
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error in bulk user import: {e}")
        return jsonify({'error': 'Internal server error during import'}), 500


@admin_bp.route('/download-user-template', methods=['GET'])
@jwt_required()
@admin_required
def download_user_template():
    """
    Download CSV template for bulk user import
    """
    try:
        # Create CSV template
        template_data = [
            ['email', 'password', 'full_name', 'phone', 'country', 'is_admin', 'group_name', 'account_type'],
            ['student1-group1@school.com', 'StudentPass123!', 'John Smith', '+1234567890', 'United States', 'false', 'Group 1', 'individual'],
            ['student2-group1@school.com', 'StudentPass123!', 'Sarah Johnson', '+1234567891', 'United States', 'false', 'Group 1', 'individual'],
            ['student3-group1@school.com', 'StudentPass123!', 'Mike Wilson', '+1234567892', 'United States', 'false', 'Group 1', 'individual'],
            ['group1@school.com', 'GroupPass123!', 'Group 1 Account', '+1234567896', 'United States', 'false', 'Group 1', 'group'],
            ['student1-group2@school.com', 'StudentPass123!', 'Lisa Brown', '+1234567893', 'United States', 'false', 'Group 2', 'individual'],
            ['student2-group2@school.com', 'StudentPass123!', 'David Chen', '+1234567894', 'United States', 'false', 'Group 2', 'individual'],
            ['group2@school.com', 'GroupPass123!', 'Group 2 Account', '+1234567897', 'United States', 'false', 'Group 2', 'group'],
            ['teacher1@school.com', 'TeacherPass123!', 'Dr. Emily Davis', '+1234567895', 'United States', 'true', '', 'admin']
        ]
        
        # Create CSV string
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerows(template_data)
        csv_string = output.getvalue()
        output.close()
        
        # Create response
        response = make_response(csv_string)
        response.headers['Content-Type'] = 'text/csv'
        response.headers['Content-Disposition'] = 'attachment; filename=bulk_users_template.csv'
        
        return response
        
    except Exception as e:
        current_app.logger.error(f"Error downloading template: {e}")
        return jsonify({'error': 'Error generating template'}), 500


# ─── GROUP MANAGEMENT ──────────────────────────────────────────────────────

@admin_bp.route('/groups', methods=['GET'])
@jwt_required()
@admin_required
def get_groups():
    """
    Get all groups with member counts and basic stats
    """
    try:
        groups = Group.query.filter_by(is_active=True).all()
        
        groups_data = []
        for group in groups:
            # Count members
            member_count = User.query.filter_by(group_id=group.id).count()
            
            # Get basic stats
            member_ids = [user.id for user in group.users]
            total_trades = 0
            if member_ids:
                total_trades = JournalEntry.query.filter(JournalEntry.user_id.in_(member_ids)).count()
            
            groups_data.append({
                'id': group.id,
                'name': group.name,
                'description': group.description,
                'member_count': member_count,
                'total_trades': total_trades,
                'created_at': group.created_at.isoformat() if group.created_at else None
            })
        
        return jsonify({
            'success': True,
            'groups': groups_data
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error getting groups: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@admin_bp.route('/groups/<int:group_id>/analytics', methods=['GET'])
@jwt_required()
@admin_required
def get_group_analytics(group_id):
    """
    Get comprehensive analytics for a specific group
    Aggregates data from all members in the group
    """
    try:
        # Validate group exists
        group = Group.query.get(group_id)
        if not group:
            return jsonify({'error': 'Group not found'}), 404
        
        # Get all users in this group
        group_users = User.query.filter_by(group_id=group_id).all()
        user_ids = [user.id for user in group_users]
        
        if not user_ids:
            return jsonify({
                'success': True,
                'group': {
                    'id': group.id,
                    'name': group.name,
                    'description': group.description,
                    'member_count': 0
                },
                'analytics': {
                    'total_trades': 0,
                    'total_pnl': 0,
                    'win_rate': 0,
                    'members': []
                }
            }), 200
        
        # Get all trades for group members
        trades = JournalEntry.query.filter(JournalEntry.user_id.in_(user_ids)).all()
        
        # Calculate group analytics
        total_trades = len(trades)
        total_pnl = sum(trade.pnl for trade in trades if trade.pnl is not None)
        winning_trades = len([trade for trade in trades if trade.pnl and trade.pnl > 0])
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        # Individual member stats
        member_stats = []
        for user in group_users:
            user_trades = [trade for trade in trades if trade.user_id == user.id]
            user_total_trades = len(user_trades)
            user_total_pnl = sum(trade.pnl for trade in user_trades if trade.pnl is not None)
            user_winning_trades = len([trade for trade in user_trades if trade.pnl and trade.pnl > 0])
            user_win_rate = (user_winning_trades / user_total_trades * 100) if user_total_trades > 0 else 0
            
            member_stats.append({
                'user_id': user.id,
                'email': user.email,
                'full_name': user.full_name,
                'total_trades': user_total_trades,
                'total_pnl': round(user_total_pnl, 2),
                'win_rate': round(user_win_rate, 2),
                'winning_trades': user_winning_trades,
                'losing_trades': user_total_trades - user_winning_trades
            })
        
        # Sort members by performance (total_pnl)
        member_stats.sort(key=lambda x: x['total_pnl'], reverse=True)
        
        # Group performance by time periods
        from datetime import datetime, timedelta
        now = datetime.utcnow()
        
        # Last 30 days trades
        last_30_days = now - timedelta(days=30)
        recent_trades = [trade for trade in trades if trade.created_at and trade.created_at >= last_30_days]
        recent_pnl = sum(trade.pnl for trade in recent_trades if trade.pnl is not None)
        
        return jsonify({
            'success': True,
            'group': {
                'id': group.id,
                'name': group.name,
                'description': group.description,
                'member_count': len(group_users),
                'created_at': group.created_at.isoformat() if group.created_at else None
            },
            'analytics': {
                'total_trades': total_trades,
                'total_pnl': round(total_pnl, 2),
                'win_rate': round(win_rate, 2),
                'winning_trades': winning_trades,
                'losing_trades': total_trades - winning_trades,
                'recent_trades_30d': len(recent_trades),
                'recent_pnl_30d': round(recent_pnl, 2),
                'average_pnl_per_trade': round(total_pnl / total_trades, 2) if total_trades > 0 else 0
            },
            'members': member_stats
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error getting group analytics: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@admin_bp.route('/groups', methods=['POST'])
@jwt_required()
@admin_required
def create_group():
    """
    Create a new group
    """
    try:
        data = request.get_json()
        name = data.get('name', '').strip()
        description = data.get('description', '').strip()
        
        if not name:
            return jsonify({'error': 'Group name is required'}), 400
        
        # Check if group already exists
        existing_group = Group.query.filter_by(name=name).first()
        if existing_group:
            return jsonify({'error': 'Group name already exists'}), 400
        
        # Create new group
        new_group = Group(
            name=name,
            description=description if description else f"Group: {name}"
        )
        
        db.session.add(new_group)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Group created successfully',
            'group': {
                'id': new_group.id,
                'name': new_group.name,
                'description': new_group.description
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating group: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@admin_bp.route('/users/<int:user_id>/login-as', methods=['POST'])
@jwt_required()
@admin_required
@rate_limit_admin(max_requests=10, window_seconds=60)
def login_as_user(user_id):
    """Generate a login token for admin to login as a specific user"""
    try:
        # Get the target user
        target_user = User.query.get(user_id)
        if not target_user:
            return jsonify({"error": "User not found"}), 404
        
        # Get the admin user making the request
        admin_user_id = get_jwt_identity()
        admin_user = User.query.get(admin_user_id)
        
        # Check if user has an active profile
        active_profile = Profile.query.filter_by(user_id=target_user.id, is_active=True).first()
        has_active_profile = active_profile is not None
        
        # Create access and refresh tokens for the target user
        access_token = create_access_token(
            identity=str(target_user.id),
            additional_claims={"is_admin": target_user.is_admin}
        )
        refresh_token = create_refresh_token(
            identity=str(target_user.id),
            additional_claims={"is_admin": target_user.is_admin}
        )
        
        # Log the admin action
        log_admin_action("Login as user", f"Admin {admin_user.email} logged in as user {target_user.email}")
        
        return jsonify({
            "message": "Login token generated successfully",
            "token": access_token,
            "refresh_token": refresh_token,
            "user": {
                "id": target_user.id,
                "email": target_user.email,
                "email_verified": target_user.email_verified,
                "is_admin": target_user.is_admin,
                "full_name": target_user.full_name,
                "has_active_profile": has_active_profile
            }
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error generating login token: {str(e)}")
        return jsonify({"error": "Failed to generate login token"}), 500


# ─── BULK EMAIL SENDING ──────────────────────────────────────────────────────

@admin_bp.route('/send-bulk-email', methods=['POST'])
@jwt_required()
@admin_required
@rate_limit_admin(max_requests=5, window_seconds=60)
def send_bulk_email():
    """
    Admin-only: Send bulk emails to multiple recipients.
    Expects JSON: { emails: [...], subject: "...", content: "..." (HTML content) }
    """
    try:
        data = request.get_json() or {}
        emails = data.get('emails', [])
        subject = data.get('subject', '').strip()
        content = data.get('content', '').strip()
        
        if not emails:
            return jsonify({"error": "No recipients specified"}), 400
        if not subject:
            return jsonify({"error": "Subject is required"}), 400
        if not content:
            return jsonify({"error": "Email content is required"}), 400
        
        # Remove duplicates while preserving order
        unique_emails = list(dict.fromkeys([e.lower().strip() for e in emails if e and '@' in e]))
        
        if not unique_emails:
            return jsonify({"error": "No valid email addresses provided"}), 400
        
        sent_count = 0
        failed_emails = []
        
        # Get sender email from config
        sender_email = current_app.config.get('MAIL_DEFAULT_SENDER') or current_app.config.get('MAIL_USERNAME')
        
        for email in unique_emails:
            try:
                msg = Message(
                    subject=subject,
                    recipients=[email],
                    html=content,
                    sender=f"Talaria <{sender_email}>"
                )
                mail.send(msg)
                sent_count += 1
            except Exception as e:
                current_app.logger.error(f"Failed to send email to {email}: {str(e)}")
                failed_emails.append({"email": email, "error": str(e)})
        
        log_admin_action("SEND_BULK_EMAIL", f"Sent {sent_count}/{len(unique_emails)} emails with subject: {subject[:50]}...")
        
        return jsonify({
            "success": True,
            "sent": sent_count,
            "total": len(unique_emails),
            "failed": len(failed_emails),
            "failed_emails": failed_emails[:10]  # Return first 10 failed emails
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error in bulk email: {str(e)}")
        return jsonify({"error": f"Failed to send bulk email: {str(e)}"}), 500


# ══════════════════════════════════════════════════════════════════════════════
# Server Monitoring Endpoints
# ══════════════════════════════════════════════════════════════════════════════

def run_shell_command(cmd, timeout=5):
    """Run a shell command and return output."""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return result.stdout.strip()
    except Exception as e:
        return f"Error: {str(e)}"


@admin_bp.route('/monitoring/overview', methods=['GET'])
@jwt_required()
@rate_limit_admin(max_requests=30, window_seconds=60)
def monitoring_overview():
    """
    Admin-only: Get complete server monitoring overview including system, security, and services.
    Works inside Docker containers using psutil and available system info.
    """
    if not is_admin_user():
        return jsonify({"error": "Only admins can view monitoring data"}), 403

    try:
        # ─── System Metrics (using psutil for Docker compatibility) ───────────────
        if PSUTIL_AVAILABLE:
            cpu_percent = psutil.cpu_percent(interval=0.5)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Get uptime
            try:
                uptime_seconds = time.time() - psutil.boot_time()
                days = int(uptime_seconds // 86400)
                hours = int((uptime_seconds % 86400) // 3600)
                minutes = int((uptime_seconds % 3600) // 60)
                uptime_str = f"up {days}d {hours}h {minutes}m" if days > 0 else f"up {hours}h {minutes}m"
            except:
                uptime_str = "N/A"
            
            # Get load average
            try:
                load_avg = psutil.getloadavg()
                load_str = f"{load_avg[0]:.2f} {load_avg[1]:.2f} {load_avg[2]:.2f}"
            except:
                load_str = "N/A"
            
            # Format disk sizes
            disk_used_gb = disk.used / (1024**3)
            disk_total_gb = disk.total / (1024**3)
            disk_percent_val = disk.percent
            
            system_data = {
                "timestamp": datetime.utcnow().isoformat(),
                "cpu": {
                    "percent": cpu_percent,
                    "status": "critical" if cpu_percent > 90 else "warning" if cpu_percent > 70 else "ok"
                },
                "memory": {
                    "used_mb": int(memory.used / (1024**2)),
                    "total_mb": int(memory.total / (1024**2)),
                    "percent": memory.percent,
                    "status": "critical" if memory.percent > 90 else "warning" if memory.percent > 70 else "ok"
                },
                "disk": {
                    "used": f"{disk_used_gb:.1f}G",
                    "total": f"{disk_total_gb:.1f}G",
                    "percent": f"{disk_percent_val}%",
                    "status": "critical" if disk_percent_val > 90 else "warning" if disk_percent_val > 70 else "ok"
                },
                "uptime": uptime_str,
                "load_average": load_str
            }
        else:
            # Fallback if psutil not available
            system_data = {
                "timestamp": datetime.utcnow().isoformat(),
                "cpu": {"percent": 0, "status": "ok"},
                "memory": {"used_mb": 0, "total_mb": 0, "percent": 0, "status": "ok"},
                "disk": {"used": "N/A", "total": "N/A", "percent": "0%", "status": "ok"},
                "uptime": "N/A",
                "load_average": "N/A"
            }
        
        # ─── Security Status (simplified for Docker) ──────────────────────────────
        # Check if we're running in Docker (can't access host security tools)
        in_docker = os.path.exists('/.dockerenv')
        
        if in_docker:
            # Running in Docker - provide info message instead of false "not installed"
            security_data = {
                "timestamp": datetime.utcnow().isoformat(),
                "fail2ban": {
                    "status": "host-level",
                    "banned_count": 0,
                    "banned_ips": [],
                    "note": "Security services run on host, not in container"
                },
                "firewall": {
                    "ufw_status": "host-level"
                },
                "recent_failed_ssh": [],
                "nginx_errors_today": 0,
                "container_mode": True
            }
        else:
            # Running on host - check actual services
            fail2ban_status = run_shell_command("systemctl is-active fail2ban 2>/dev/null || echo 'not installed'")
            ufw_status = run_shell_command("ufw status 2>/dev/null | head -1 || echo 'not installed'")
            
            banned_ips = []
            if fail2ban_status == "active":
                banned_output = run_shell_command("fail2ban-client banned 2>/dev/null || echo '[]'")
                try:
                    import ast
                    banned_data = ast.literal_eval(banned_output)
                    if banned_data and isinstance(banned_data, list):
                        for jail in banned_data:
                            if isinstance(jail, dict):
                                for jail_name, ips in jail.items():
                                    for ip in ips:
                                        banned_ips.append({"ip": ip, "jail": jail_name})
                except:
                    pass
            
            failed_ssh = run_shell_command("grep 'Failed password' /var/log/auth.log 2>/dev/null | tail -5 | awk '{print $1, $2, $3, $11}' || echo ''")
            error_count = run_shell_command("grep -a ' 4[0-9][0-9] \\| 5[0-9][0-9] ' /var/log/nginx/access.log 2>/dev/null | wc -l || echo '0'")
            
            security_data = {
                "timestamp": datetime.utcnow().isoformat(),
                "fail2ban": {
                    "status": fail2ban_status,
                    "banned_count": len(banned_ips),
                    "banned_ips": banned_ips[:10]
                },
                "firewall": {
                    "ufw_status": ufw_status
                },
                "recent_failed_ssh": [s for s in failed_ssh.split("\n") if s.strip()] if failed_ssh else [],
                "nginx_errors_today": int(error_count) if error_count.isdigit() else 0,
                "container_mode": False
            }
        
        # ─── Services Status ──────────────────────────────────────────────────────
        if in_docker:
            # In Docker - show container is running
            services_data = {
                "timestamp": datetime.utcnow().isoformat(),
                "services": [
                    {"name": "journal-backend", "status": "active", "ok": True},
                    {"name": "database", "status": "active", "ok": True}
                ],
                "docker_containers": ["Running in containerized environment"],
                "container_mode": True
            }
        else:
            services = ["nginx", "docker", "fail2ban", "ufw"]
            status_list = []
            for service in services:
                status = run_shell_command(f"systemctl is-active {service} 2>/dev/null || echo 'not found'")
                status_list.append({
                    "name": service,
                    "status": status,
                    "ok": status == "active"
                })
            
            docker_ps = run_shell_command("docker ps --format '{{.Names}}: {{.Status}}' 2>/dev/null | head -10 || echo ''")
            
            services_data = {
                "timestamp": datetime.utcnow().isoformat(),
                "services": status_list,
                "docker_containers": [c for c in docker_ps.split("\n") if c.strip()] if docker_ps else [],
                "container_mode": False
            }
        
        # ─── Calculate Overall Health ─────────────────────────────────────────────
        issues = []
        if system_data["cpu"]["status"] == "critical":
            issues.append("High CPU usage")
        if system_data["memory"]["status"] == "critical":
            issues.append("High memory usage")
        if system_data["disk"]["status"] == "critical":
            issues.append("Low disk space")
        
        # Only check security services if not in Docker
        if not in_docker:
            if security_data["fail2ban"]["status"] != "active":
                issues.append("Fail2Ban not running")
            for svc in services_data["services"]:
                if svc["name"] in ["nginx", "docker"] and not svc["ok"]:
                    issues.append(f"{svc['name']} is down")
        
        health_status = "critical" if len(issues) > 2 else "warning" if len(issues) > 0 else "healthy"
        
        log_admin_action("VIEW_MONITORING", f"Server monitoring check - Status: {health_status}")
        
        return jsonify({
            "timestamp": datetime.utcnow().isoformat(),
            "health_status": health_status,
            "issues": issues,
            "system": system_data,
            "security": security_data,
            "services": services_data,
            "running_in_container": in_docker
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error in monitoring overview: {str(e)}")
        return jsonify({"error": f"Failed to get monitoring data: {str(e)}"}), 500


# ══════════════════════════════════════════════════════════════════════════════
# Application-Level Security Endpoints
# ══════════════════════════════════════════════════════════════════════════════

@admin_bp.route('/security/blocked-ips', methods=['GET'])
@jwt_required()
@rate_limit_admin(max_requests=30, window_seconds=60)
def get_blocked_ips():
    """Get all blocked IP addresses."""
    if not is_admin_user():
        return jsonify({"error": "Admin access required"}), 403
    
    try:
        blocked = BlockedIP.query.order_by(BlockedIP.blocked_at.desc()).all()
        return jsonify({
            "blocked_ips": [{
                "id": ip.id,
                "ip_address": ip.ip_address,
                "reason": ip.reason,
                "blocked_at": ip.blocked_at.isoformat() if ip.blocked_at else None,
                "blocked_until": ip.blocked_until.isoformat() if ip.blocked_until else None,
                "failed_attempts": ip.failed_attempts,
                "is_permanent": ip.is_permanent,
                "is_active": ip.is_active(),
                "blocked_by": ip.blocked_by
            } for ip in blocked],
            "total": len(blocked),
            "active_count": sum(1 for ip in blocked if ip.is_active())
        }), 200
    except Exception as e:
        current_app.logger.error(f"Error fetching blocked IPs: {str(e)}")
        return jsonify({"error": "Failed to fetch blocked IPs"}), 500


@admin_bp.route('/security/block-ip', methods=['POST'])
@jwt_required()
@rate_limit_admin(max_requests=30, window_seconds=60)
def block_ip():
    """Manually block an IP address."""
    if not is_admin_user():
        return jsonify({"error": "Admin access required"}), 403
    
    try:
        data = request.get_json()
        ip_address = data.get('ip_address', '').strip()
        reason = data.get('reason', 'Manually blocked by admin')
        is_permanent = data.get('is_permanent', False)
        duration_hours = data.get('duration_hours', 24)
        
        if not ip_address:
            return jsonify({"error": "IP address is required"}), 400
        
        # Check if already blocked
        existing = BlockedIP.query.filter_by(ip_address=ip_address).first()
        if existing:
            existing.reason = reason
            existing.is_permanent = is_permanent
            existing.blocked_until = None if is_permanent else datetime.utcnow() + timedelta(hours=duration_hours)
            existing.blocked_by = get_jwt_identity()
            db.session.commit()
            log_admin_action("UPDATE_BLOCKED_IP", f"Updated block for IP: {ip_address}")
            return jsonify({"message": f"Updated block for {ip_address}"}), 200
        
        # Create new block
        blocked_until = None if is_permanent else datetime.utcnow() + timedelta(hours=duration_hours)
        new_block = BlockedIP(
            ip_address=ip_address,
            reason=reason,
            is_permanent=is_permanent,
            blocked_until=blocked_until,
            blocked_by=get_jwt_identity()
        )
        db.session.add(new_block)
        
        # Log security event
        log_entry = SecurityLog(
            ip_address=ip_address,
            event_type='manual_block',
            details=f"Blocked by admin: {reason}"
        )
        db.session.add(log_entry)
        db.session.commit()
        
        log_admin_action("BLOCK_IP", f"Blocked IP: {ip_address} - {reason}")
        return jsonify({"message": f"Successfully blocked {ip_address}"}), 201
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error blocking IP: {str(e)}")
        return jsonify({"error": "Failed to block IP"}), 500


@admin_bp.route('/security/unblock-ip/<int:block_id>', methods=['DELETE'])
@jwt_required()
@rate_limit_admin(max_requests=30, window_seconds=60)
def unblock_ip(block_id):
    """Unblock an IP address."""
    if not is_admin_user():
        return jsonify({"error": "Admin access required"}), 403
    
    try:
        blocked = BlockedIP.query.get(block_id)
        if not blocked:
            return jsonify({"error": "Blocked IP not found"}), 404
        
        ip_address = blocked.ip_address
        db.session.delete(blocked)
        
        # Log security event
        log_entry = SecurityLog(
            ip_address=ip_address,
            event_type='unblock',
            details=f"Unblocked by admin: {get_jwt_identity()}"
        )
        db.session.add(log_entry)
        db.session.commit()
        
        log_admin_action("UNBLOCK_IP", f"Unblocked IP: {ip_address}")
        return jsonify({"message": f"Successfully unblocked {ip_address}"}), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error unblocking IP: {str(e)}")
        return jsonify({"error": "Failed to unblock IP"}), 500


@admin_bp.route('/security/logs', methods=['GET'])
@jwt_required()
@rate_limit_admin(max_requests=30, window_seconds=60)
def get_security_logs():
    """Get security event logs."""
    if not is_admin_user():
        return jsonify({"error": "Admin access required"}), 403
    
    try:
        limit = request.args.get('limit', 100, type=int)
        event_type = request.args.get('event_type', None)
        
        query = SecurityLog.query
        if event_type:
            query = query.filter_by(event_type=event_type)
        
        logs = query.order_by(SecurityLog.created_at.desc()).limit(limit).all()
        
        return jsonify({
            "logs": [{
                "id": log.id,
                "ip_address": log.ip_address,
                "event_type": log.event_type,
                "details": log.details,
                "endpoint": log.endpoint,
                "created_at": log.created_at.isoformat() if log.created_at else None
            } for log in logs],
            "total": len(logs)
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error fetching security logs: {str(e)}")
        return jsonify({"error": "Failed to fetch security logs"}), 500


@admin_bp.route('/security/failed-logins', methods=['GET'])
@jwt_required()
@rate_limit_admin(max_requests=30, window_seconds=60)
def get_failed_logins():
    """Get failed login attempts summary."""
    if not is_admin_user():
        return jsonify({"error": "Admin access required"}), 403
    
    try:
        # Get failed attempts in last 24 hours
        since = datetime.utcnow() - timedelta(hours=24)
        
        # Group by IP address
        from sqlalchemy import func
        failed_by_ip = db.session.query(
            FailedLoginAttempt.ip_address,
            func.count(FailedLoginAttempt.id).label('count'),
            func.max(FailedLoginAttempt.attempted_at).label('last_attempt')
        ).filter(
            FailedLoginAttempt.attempted_at >= since
        ).group_by(
            FailedLoginAttempt.ip_address
        ).order_by(
            func.count(FailedLoginAttempt.id).desc()
        ).limit(50).all()
        
        return jsonify({
            "failed_logins": [{
                "ip_address": row[0],
                "attempts": row[1],
                "last_attempt": row[2].isoformat() if row[2] else None
            } for row in failed_by_ip],
            "total_failed_24h": sum(row[1] for row in failed_by_ip)
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error fetching failed logins: {str(e)}")
        return jsonify({"error": "Failed to fetch failed login data"}), 500


@admin_bp.route('/security/stats', methods=['GET'])
@jwt_required()
@rate_limit_admin(max_requests=30, window_seconds=60)
def get_security_stats():
    """Get security statistics for dashboard."""
    if not is_admin_user():
        return jsonify({"error": "Admin access required"}), 403
    
    try:
        from sqlalchemy import func
        
        # Count blocked IPs
        blocked_count = BlockedIP.query.count()
        active_blocks = sum(1 for ip in BlockedIP.query.all() if ip.is_active())
        
        # Failed logins in last 24 hours
        since_24h = datetime.utcnow() - timedelta(hours=24)
        failed_24h = FailedLoginAttempt.query.filter(
            FailedLoginAttempt.attempted_at >= since_24h
        ).count()
        
        # Security events in last 24 hours
        events_24h = SecurityLog.query.filter(
            SecurityLog.created_at >= since_24h
        ).count()
        
        # Unique IPs with failed logins
        unique_failed_ips = db.session.query(
            func.count(func.distinct(FailedLoginAttempt.ip_address))
        ).filter(
            FailedLoginAttempt.attempted_at >= since_24h
        ).scalar() or 0
        
        return jsonify({
            "blocked_ips_total": blocked_count,
            "blocked_ips_active": active_blocks,
            "failed_logins_24h": failed_24h,
            "security_events_24h": events_24h,
            "unique_threat_ips": unique_failed_ips,
            "protection_status": "active"
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error fetching security stats: {str(e)}")
        return jsonify({"error": "Failed to fetch security stats"}), 500


# ============== ANALYTICS ENDPOINTS ==============

@admin_bp.route('/analytics/overview', methods=['GET'])
@jwt_required()
@rate_limit_admin(max_requests=30, window_seconds=60)
def get_analytics_overview():
    """Get comprehensive analytics overview"""
    if not is_admin_user():
        return jsonify({"error": "Admin access required"}), 403
    
    try:
        from sqlalchemy import func
        
        now = datetime.utcnow()
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)
        
        # User Stats
        total_users = User.query.count()
        active_users = User.query.filter_by(is_active=True).count()
        new_users_today = User.query.filter(User.created_at >= today).count()
        new_users_week = User.query.filter(User.created_at >= week_ago).count()
        new_users_month = User.query.filter(User.created_at >= month_ago).count()
        
        # Users with journal access
        journal_users = User.query.filter_by(has_journal_access=True).count()
        
        # Trade Stats
        total_trades = JournalEntry.query.count()
        trades_today = JournalEntry.query.filter(JournalEntry.created_at >= today).count()
        trades_week = JournalEntry.query.filter(JournalEntry.created_at >= week_ago).count()
        trades_month = JournalEntry.query.filter(JournalEntry.created_at >= month_ago).count()
        
        # Win rate calculation
        winning_trades = JournalEntry.query.filter(JournalEntry.pnl > 0).count()
        losing_trades = JournalEntry.query.filter(JournalEntry.pnl < 0).count()
        win_rate = round((winning_trades / total_trades * 100), 1) if total_trades > 0 else 0
        
        # Total PnL
        total_pnl = db.session.query(func.sum(JournalEntry.pnl)).scalar() or 0
        
        # Profile Stats
        total_profiles = Profile.query.count()
        active_profiles = Profile.query.filter_by(is_active=True).count()
        
        # Group Stats
        total_groups = Group.query.count()
        active_groups = Group.query.filter_by(is_active=True).count()
        
        return jsonify({
            "users": {
                "total": total_users,
                "active": active_users,
                "inactive": total_users - active_users,
                "with_journal_access": journal_users,
                "new_today": new_users_today,
                "new_this_week": new_users_week,
                "new_this_month": new_users_month
            },
            "trades": {
                "total": total_trades,
                "today": trades_today,
                "this_week": trades_week,
                "this_month": trades_month,
                "winning": winning_trades,
                "losing": losing_trades,
                "win_rate": win_rate,
                "total_pnl": round(float(total_pnl), 2)
            },
            "profiles": {
                "total": total_profiles,
                "active": active_profiles
            },
            "groups": {
                "total": total_groups,
                "active": active_groups
            }
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Analytics overview error: {str(e)}")
        return jsonify({"error": "Failed to fetch analytics"}), 500


@admin_bp.route('/analytics/user-growth', methods=['GET'])
@jwt_required()
@rate_limit_admin(max_requests=30, window_seconds=60)
def get_user_growth():
    """Get user registration data over time"""
    if not is_admin_user():
        return jsonify({"error": "Admin access required"}), 403
    
    try:
        from sqlalchemy import func
        
        days = request.args.get('days', 30, type=int)
        days = min(days, 365)  # Max 1 year
        
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Get daily registrations
        daily_data = db.session.query(
            func.date(User.created_at).label('date'),
            func.count(User.id).label('count')
        ).filter(
            User.created_at >= start_date
        ).group_by(
            func.date(User.created_at)
        ).order_by(
            func.date(User.created_at)
        ).all()
        
        # Format for chart
        chart_data = []
        for row in daily_data:
            chart_data.append({
                "date": str(row.date),
                "registrations": row.count
            })
        
        # Calculate cumulative growth
        cumulative = 0
        for item in chart_data:
            cumulative += item['registrations']
            item['cumulative'] = cumulative
        
        return jsonify({
            "period_days": days,
            "data": chart_data,
            "total_new_users": sum(item['registrations'] for item in chart_data)
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"User growth error: {str(e)}")
        return jsonify({"error": "Failed to fetch user growth data"}), 500


@admin_bp.route('/analytics/trade-activity', methods=['GET'])
@jwt_required()
@rate_limit_admin(max_requests=30, window_seconds=60)
def get_trade_activity():
    """Get trading activity over time"""
    if not is_admin_user():
        return jsonify({"error": "Admin access required"}), 403
    
    try:
        from sqlalchemy import func
        
        days = request.args.get('days', 30, type=int)
        days = min(days, 365)
        
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Daily trades
        daily_trades = db.session.query(
            func.date(JournalEntry.date).label('date'),
            func.count(JournalEntry.id).label('trades'),
            func.sum(JournalEntry.pnl).label('pnl'),
            func.sum(db.case((JournalEntry.pnl > 0, 1), else_=0)).label('wins'),
            func.sum(db.case((JournalEntry.pnl < 0, 1), else_=0)).label('losses')
        ).filter(
            JournalEntry.date >= start_date
        ).group_by(
            func.date(JournalEntry.date)
        ).order_by(
            func.date(JournalEntry.date)
        ).all()
        
        chart_data = []
        for row in daily_trades:
            total = row.wins + row.losses
            chart_data.append({
                "date": str(row.date),
                "trades": row.trades,
                "pnl": round(float(row.pnl or 0), 2),
                "wins": row.wins,
                "losses": row.losses,
                "win_rate": round((row.wins / total * 100), 1) if total > 0 else 0
            })
        
        return jsonify({
            "period_days": days,
            "data": chart_data
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Trade activity error: {str(e)}")
        return jsonify({"error": "Failed to fetch trade activity"}), 500


@admin_bp.route('/analytics/top-symbols', methods=['GET'])
@jwt_required()
@rate_limit_admin(max_requests=30, window_seconds=60)
def get_top_symbols():
    """Get most traded symbols"""
    if not is_admin_user():
        return jsonify({"error": "Admin access required"}), 403
    
    try:
        from sqlalchemy import func
        
        limit = request.args.get('limit', 10, type=int)
        
        # Top traded symbols
        top_symbols = db.session.query(
            JournalEntry.symbol,
            func.count(JournalEntry.id).label('trade_count'),
            func.sum(JournalEntry.pnl).label('total_pnl'),
            func.avg(JournalEntry.pnl).label('avg_pnl'),
            func.sum(db.case((JournalEntry.pnl > 0, 1), else_=0)).label('wins')
        ).group_by(
            JournalEntry.symbol
        ).order_by(
            func.count(JournalEntry.id).desc()
        ).limit(limit).all()
        
        symbols_data = []
        for row in top_symbols:
            win_rate = round((row.wins / row.trade_count * 100), 1) if row.trade_count > 0 else 0
            symbols_data.append({
                "symbol": row.symbol,
                "trades": row.trade_count,
                "total_pnl": round(float(row.total_pnl or 0), 2),
                "avg_pnl": round(float(row.avg_pnl or 0), 2),
                "win_rate": win_rate
            })
        
        return jsonify({"symbols": symbols_data}), 200
        
    except Exception as e:
        current_app.logger.error(f"Top symbols error: {str(e)}")
        return jsonify({"error": "Failed to fetch top symbols"}), 500


@admin_bp.route('/analytics/user-activity', methods=['GET'])
@jwt_required()
@rate_limit_admin(max_requests=30, window_seconds=60)
def get_user_activity():
    """Get most active users by trade count"""
    if not is_admin_user():
        return jsonify({"error": "Admin access required"}), 403
    
    try:
        from sqlalchemy import func
        
        limit = request.args.get('limit', 10, type=int)
        
        # Most active traders
        active_users = db.session.query(
            User.id,
            User.name,
            User.email,
            func.count(JournalEntry.id).label('trade_count'),
            func.sum(JournalEntry.pnl).label('total_pnl')
        ).join(
            JournalEntry, User.id == JournalEntry.user_id
        ).group_by(
            User.id, User.name, User.email
        ).order_by(
            func.count(JournalEntry.id).desc()
        ).limit(limit).all()
        
        users_data = []
        for row in active_users:
            users_data.append({
                "id": row.id,
                "name": row.name,
                "email": row.email,
                "trades": row.trade_count,
                "total_pnl": round(float(row.total_pnl or 0), 2)
            })
        
        return jsonify({"users": users_data}), 200
        
    except Exception as e:
        current_app.logger.error(f"User activity error: {str(e)}")
        return jsonify({"error": "Failed to fetch user activity"}), 500


@admin_bp.route('/analytics/system-stats', methods=['GET'])
@jwt_required()
@rate_limit_admin(max_requests=30, window_seconds=60)
def get_system_stats():
    """Get system and database statistics"""
    if not is_admin_user():
        return jsonify({"error": "Admin access required"}), 403
    
    try:
        from sqlalchemy import func
        
        # Database table sizes
        table_stats = {
            "users": User.query.count(),
            "journal_entries": JournalEntry.query.count(),
            "profiles": Profile.query.count(),
            "groups": Group.query.count(),
            "blocked_ips": BlockedIP.query.count(),
            "security_logs": SecurityLog.query.count(),
            "failed_logins": FailedLoginAttempt.query.count()
        }
        
        # System metrics if psutil available
        system_metrics = {}
        if PSUTIL_AVAILABLE:
            system_metrics = {
                "cpu_percent": psutil.cpu_percent(interval=0.1),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_percent": psutil.disk_usage('/').percent
            }
        
        # Recent activity (last 24h)
        since_24h = datetime.utcnow() - timedelta(hours=24)
        recent_stats = {
            "new_users_24h": User.query.filter(User.created_at >= since_24h).count(),
            "new_trades_24h": JournalEntry.query.filter(JournalEntry.created_at >= since_24h).count(),
            "security_events_24h": SecurityLog.query.filter(SecurityLog.created_at >= since_24h).count()
        }
        
        return jsonify({
            "database": table_stats,
            "system": system_metrics,
            "recent_activity": recent_stats
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"System stats error: {str(e)}")
        return jsonify({"error": "Failed to fetch system stats"}), 500


@admin_bp.route('/analytics/groups', methods=['GET'])
@jwt_required()
@rate_limit_admin(max_requests=30, window_seconds=60)
def get_groups_analytics_summary():
    """Get analytics per group"""
    if not is_admin_user():
        return jsonify({"error": "Admin access required"}), 403
    
    try:
        from sqlalchemy import func
        
        # Group stats with user counts
        groups_data = db.session.query(
            Group.id,
            Group.name,
            Group.is_active,
            func.count(User.id).label('user_count')
        ).outerjoin(
            User, Group.id == User.group_id
        ).group_by(
            Group.id, Group.name, Group.is_active
        ).all()
        
        result = []
        for group in groups_data:
            # Get trade count for this group
            trade_count = db.session.query(func.count(JournalEntry.id)).join(
                User, JournalEntry.user_id == User.id
            ).filter(User.group_id == group.id).scalar() or 0
            
            result.append({
                "id": group.id,
                "name": group.name,
                "is_active": group.is_active,
                "user_count": group.user_count,
                "trade_count": trade_count
            })
        
        return jsonify({"groups": result}), 200
        
    except Exception as e:
        current_app.logger.error(f"Group analytics error: {str(e)}")
        return jsonify({"error": "Failed to fetch group analytics"}), 500


# ==================== Security Settings Endpoints ====================

# Default security settings
DEFAULT_SECURITY_SETTINGS = {
    'max_failed_attempts': {'value': '10', 'description': 'Maximum failed login attempts before IP block'},
    'block_duration_hours': {'value': '24', 'description': 'Duration in hours to block an IP'},
    'alert_threshold': {'value': '5', 'description': 'Failed attempts before sending alert email'},
    'failed_attempt_window_hours': {'value': '1', 'description': 'Time window to count failed attempts'},
    'session_timeout_minutes': {'value': '60', 'description': 'Session timeout in minutes'},
    'require_strong_password': {'value': 'true', 'description': 'Require strong passwords'},
    'min_password_length': {'value': '8', 'description': 'Minimum password length'},
    'auto_block_enabled': {'value': 'true', 'description': 'Enable automatic IP blocking'},
    'alert_email_enabled': {'value': 'true', 'description': 'Send email alerts on security events'},
}


@admin_bp.route('/settings/security', methods=['GET'])
@jwt_required()
@rate_limit_admin(max_requests=30, window_seconds=60)
def get_security_settings():
    """Get all security settings"""
    if not is_admin_user():
        return jsonify({"error": "Admin access required"}), 403
    
    try:
        settings = {}
        for key, defaults in DEFAULT_SECURITY_SETTINGS.items():
            db_setting = SystemSettings.query.filter_by(key=key).first()
            if db_setting:
                settings[key] = {
                    'value': db_setting.value,
                    'description': defaults['description'],
                    'updated_at': db_setting.updated_at.isoformat() if db_setting.updated_at else None
                }
            else:
                settings[key] = {
                    'value': defaults['value'],
                    'description': defaults['description'],
                    'updated_at': None
                }
        
        return jsonify({"settings": settings}), 200
        
    except Exception as e:
        current_app.logger.error(f"Get security settings error: {str(e)}")
        return jsonify({"error": "Failed to fetch security settings"}), 500


@admin_bp.route('/settings/security', methods=['PUT'])
@jwt_required()
@rate_limit_admin(max_requests=10, window_seconds=60)
def update_security_settings():
    """Update security settings"""
    if not is_admin_user():
        return jsonify({"error": "Admin access required"}), 403
    
    try:
        data = request.get_json()
        user_id = get_jwt_identity()
        updated_keys = []
        
        for key, value in data.items():
            if key in DEFAULT_SECURITY_SETTINGS:
                SystemSettings.set_setting(
                    key=key,
                    value=str(value),
                    description=DEFAULT_SECURITY_SETTINGS[key]['description'],
                    user_id=user_id
                )
                updated_keys.append(key)
        
        # Log the settings change
        log_admin_action(user_id, 'security_settings_updated', f"Updated: {', '.join(updated_keys)}")
        
        return jsonify({
            "message": "Security settings updated successfully",
            "updated": updated_keys
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Update security settings error: {str(e)}")
        return jsonify({"error": "Failed to update security settings"}), 500


@admin_bp.route('/settings/security/reset', methods=['POST'])
@jwt_required()
@rate_limit_admin(max_requests=5, window_seconds=60)
def reset_security_settings():
    """Reset security settings to defaults"""
    if not is_admin_user():
        return jsonify({"error": "Admin access required"}), 403
    
    try:
        user_id = get_jwt_identity()
        
        for key, defaults in DEFAULT_SECURITY_SETTINGS.items():
            SystemSettings.set_setting(
                key=key,
                value=defaults['value'],
                description=defaults['description'],
                user_id=user_id
            )
        
        log_admin_action(user_id, 'security_settings_reset', "Reset all security settings to defaults")
        
        return jsonify({"message": "Security settings reset to defaults"}), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Reset security settings error: {str(e)}")
        return jsonify({"error": "Failed to reset security settings"}), 500


def get_security_setting(key, default=None):
    """Helper function to get a security setting value"""
    setting = SystemSettings.query.filter_by(key=key).first()
    if setting:
        return setting.value
    return DEFAULT_SECURITY_SETTINGS.get(key, {}).get('value', default)


# ==================== Geography/Demographics Analytics ====================

@admin_bp.route('/analytics/geography', methods=['GET'])
@jwt_required()
@rate_limit_admin(max_requests=30, window_seconds=60)
def get_geography_analytics():
    """Get geography and demographics analytics for users"""
    if not is_admin_user():
        return jsonify({"error": "Admin access required"}), 403
    
    try:
        from sqlalchemy import func, case
        
        # Get filter parameter
        user_filter = request.args.get('filter', 'all')  # all, journal, no-journal, mentorship
        
        # Base query
        query = User.query
        
        # Apply filters
        if user_filter == 'journal':
            query = query.filter(User.has_journal_access == True)
        elif user_filter == 'no-journal':
            query = query.filter(User.has_journal_access == False)
        elif user_filter == 'mentorship':
            # Get mentorship applicants from bootcamp_registrations or a specific criteria
            # For now, filter users who registered recently and don't have journal access
            query = query.filter(User.has_journal_access == False)
        
        # Get all users matching filter
        users = query.all()
        total_users = len(users)
        
        # Country distribution
        country_counts = {}
        for user in users:
            country = user.country if hasattr(user, 'country') and user.country else 'Unknown'
            country_counts[country] = country_counts.get(country, 0) + 1
        
        # Sort by count and get top countries
        sorted_countries = sorted(country_counts.items(), key=lambda x: x[1], reverse=True)
        top_countries = [{"country": c, "count": n, "percentage": round(n/total_users*100, 1) if total_users > 0 else 0} for c, n in sorted_countries[:15]]
        
        # Age distribution (from birth_date in User model)
        age_distribution = {"18-24": 0, "25-34": 0, "35-44": 0, "45-54": 0, "55+": 0, "Unknown": 0}
        current_year = datetime.utcnow().year
        
        for user in users:
            if user.birth_date:
                try:
                    age = current_year - user.birth_date.year
                    if age < 18:
                        age_distribution["18-24"] += 1
                    elif age < 25:
                        age_distribution["18-24"] += 1
                    elif age < 35:
                        age_distribution["25-34"] += 1
                    elif age < 45:
                        age_distribution["35-44"] += 1
                    elif age < 55:
                        age_distribution["45-54"] += 1
                    else:
                        age_distribution["55+"] += 1
                except:
                    age_distribution["Unknown"] += 1
            else:
                age_distribution["Unknown"] += 1
        
        # Registration trends (last 12 months)
        twelve_months_ago = datetime.utcnow() - timedelta(days=365)
        monthly_registrations = db.session.query(
            func.date_trunc('month', User.created_at).label('month'),
            func.count(User.id).label('count')
        ).filter(
            User.created_at >= twelve_months_ago,
            User.id.in_([u.id for u in users])
        ).group_by(
            func.date_trunc('month', User.created_at)
        ).order_by('month').all()
        
        registration_trend = [
            {"month": m.strftime('%Y-%m') if m else 'Unknown', "count": c}
            for m, c in monthly_registrations
        ]
        
        # User type breakdown
        journal_users = sum(1 for u in users if u.has_journal_access)
        no_journal_users = total_users - journal_users
        admin_users = sum(1 for u in users if u.role == 'admin')
        
        # Active users (logged in last 30 days) - approximate by checking recent entries
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        active_user_ids = db.session.query(JournalEntry.user_id).filter(
            JournalEntry.created_at >= thirty_days_ago,
            JournalEntry.user_id.in_([u.id for u in users])
        ).distinct().all()
        active_users = len(active_user_ids)
        
        # Email domain distribution
        email_domains = {}
        for user in users:
            if user.email and '@' in user.email:
                domain = user.email.split('@')[1].lower()
                email_domains[domain] = email_domains.get(domain, 0) + 1
        
        sorted_domains = sorted(email_domains.items(), key=lambda x: x[1], reverse=True)
        top_domains = [{"domain": d, "count": n} for d, n in sorted_domains[:10]]
        
        return jsonify({
            "total_users": total_users,
            "filter": user_filter,
            "countries": top_countries,
            "all_countries": [{"country": c, "count": n} for c, n in sorted_countries],
            "age_distribution": [{"range": k, "count": v} for k, v in age_distribution.items()],
            "registration_trend": registration_trend,
            "user_breakdown": {
                "journal_users": journal_users,
                "no_journal_users": no_journal_users,
                "admin_users": admin_users,
                "active_users": active_users
            },
            "email_domains": top_domains
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Geography analytics error: {str(e)}")
        return jsonify({"error": "Failed to fetch geography analytics"}), 500
