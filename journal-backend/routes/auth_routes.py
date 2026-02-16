# routes/auth_routes.py

from flask import Blueprint, request, jsonify, current_app
from werkzeug.security import check_password_hash, generate_password_hash
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity, get_jwt
from models import db, User, Profile, BlockedIP, SecurityLog, FailedLoginAttempt
from email_service import send_verification_email, send_password_reset_email, send_welcome_email
from email_validator import validate_email, check_domain_typo, is_blocked_domain
from passlib.context import CryptContext
from datetime import datetime, timedelta
import os

# Security settings
MAX_FAILED_ATTEMPTS = 10  # Block after 10 failed attempts
BLOCK_DURATION_HOURS = 24  # Block for 24 hours
FAILED_ATTEMPT_WINDOW_HOURS = 1  # Count attempts within 1 hour
ALERT_THRESHOLD = 5  # Send alert after 5 failed attempts (before block)
ADMIN_EMAIL = os.environ.get('ADMIN_ALERT_EMAIL', 'contact@talaria.services')


def send_security_alert(subject, message, ip_address, event_type='attack_detected'):
    """Send security alert email to admin."""
    try:
        from flask_mail import Message
        from app import mail
        
        html_content = f'''
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #dc2626 0%, #b91c1c 100%); padding: 20px; border-radius: 10px 10px 0 0;">
                <h1 style="color: white; margin: 0; font-size: 24px;">🚨 Security Alert</h1>
            </div>
            <div style="background: #1e293b; padding: 30px; border-radius: 0 0 10px 10px; color: #e2e8f0;">
                <h2 style="color: #f87171; margin-top: 0;">{subject}</h2>
                <div style="background: #0f172a; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <p style="margin: 0; color: #94a3b8;"><strong>IP Address:</strong> <span style="color: #ef4444; font-family: monospace;">{ip_address}</span></p>
                    <p style="margin: 10px 0 0 0; color: #94a3b8;"><strong>Event Type:</strong> {event_type}</p>
                    <p style="margin: 10px 0 0 0; color: #94a3b8;"><strong>Time:</strong> {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC</p>
                </div>
                <p style="color: #cbd5e1;">{message}</p>
                <div style="margin-top: 20px; padding: 15px; background: #fef3c7; border-radius: 8px; border-left: 4px solid #f59e0b;">
                    <p style="margin: 0; color: #92400e; font-size: 14px;">
                        <strong>Action Required:</strong> Review this activity in the Admin Dashboard → Health → Security section.
                    </p>
                </div>
            </div>
            <p style="text-align: center; color: #64748b; font-size: 12px; margin-top: 20px;">
                Talaria Trading Journal Security System
            </p>
        </div>
        '''
        
        msg = Message(
            subject=f"🚨 {subject}",
            sender=('Talaria Security', os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@talaria.services')),
            recipients=[ADMIN_EMAIL],
            html=html_content
        )
        mail.send(msg)
        current_app.logger.info(f"Security alert sent: {subject}")
        return True
    except Exception as e:
        current_app.logger.error(f"Failed to send security alert: {str(e)}")
        return False


def get_client_ip():
    """Get the real client IP address."""
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    if request.headers.get('X-Real-IP'):
        return request.headers.get('X-Real-IP')
    return request.remote_addr or 'unknown'


def is_ip_blocked(ip_address):
    """Check if an IP is blocked."""
    blocked = BlockedIP.query.filter_by(ip_address=ip_address).first()
    if blocked and blocked.is_active():
        return True
    return False


def record_failed_login(ip_address, email_attempted=None):
    """Record a failed login attempt and auto-block if threshold exceeded."""
    try:
        # Record the failed attempt
        attempt = FailedLoginAttempt(
            ip_address=ip_address,
            email_attempted=email_attempted,
            user_agent=request.headers.get('User-Agent', '')[:500]
        )
        db.session.add(attempt)
        
        # Count recent failed attempts from this IP
        since = datetime.utcnow() - timedelta(hours=FAILED_ATTEMPT_WINDOW_HOURS)
        recent_attempts = FailedLoginAttempt.query.filter(
            FailedLoginAttempt.ip_address == ip_address,
            FailedLoginAttempt.attempted_at >= since
        ).count()
        
        # Send warning alert at threshold (before block)
        if recent_attempts == ALERT_THRESHOLD:
            send_security_alert(
                subject="Suspicious Login Activity Detected",
                message=f"Multiple failed login attempts ({recent_attempts}) detected from IP address {ip_address}. "
                        f"Targeted email: {email_attempted or 'Unknown'}. "
                        f"The IP will be automatically blocked after {MAX_FAILED_ATTEMPTS} attempts.",
                ip_address=ip_address,
                event_type='suspicious_activity'
            )
        
        # Auto-block if too many failures
        if recent_attempts >= MAX_FAILED_ATTEMPTS:
            existing_block = BlockedIP.query.filter_by(ip_address=ip_address).first()
            if not existing_block:
                new_block = BlockedIP(
                    ip_address=ip_address,
                    reason=f"Auto-blocked: {recent_attempts} failed login attempts",
                    blocked_until=datetime.utcnow() + timedelta(hours=BLOCK_DURATION_HOURS),
                    failed_attempts=recent_attempts,
                    blocked_by='system'
                )
                db.session.add(new_block)
                
                # Log security event
                log_entry = SecurityLog(
                    ip_address=ip_address,
                    event_type='auto_block',
                    details=f"Auto-blocked after {recent_attempts} failed login attempts. Target: {email_attempted}",
                    endpoint='/auth/login'
                )
                db.session.add(log_entry)
                
                # Send CRITICAL alert for auto-block
                send_security_alert(
                    subject="⛔ IP Address Auto-Blocked",
                    message=f"IP address {ip_address} has been automatically blocked after {recent_attempts} failed login attempts. "
                            f"Targeted email: {email_attempted or 'Unknown'}. "
                            f"Block duration: {BLOCK_DURATION_HOURS} hours. "
                            f"User Agent: {request.headers.get('User-Agent', 'Unknown')[:100]}",
                    ip_address=ip_address,
                    event_type='ip_blocked'
                )
        
        db.session.commit()
        return recent_attempts
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error recording failed login: {str(e)}")
        return 0


def clear_failed_attempts(ip_address):
    """Clear failed login attempts after successful login."""
    try:
        FailedLoginAttempt.query.filter_by(ip_address=ip_address).delete()
        db.session.commit()
    except:
        db.session.rollback()

# Support both werkzeug and passlib password hashing (for compatibility with trading-chart backend)
_pwd_passlib = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

def verify_password_compat(stored_hash, password):
    """Verify password against both werkzeug and passlib hash formats."""
    # Try werkzeug first
    try:
        if check_password_hash(stored_hash, password):
            return True
    except (ValueError, TypeError):
        pass
    
    # Try passlib (used by trading-chart backend)
    try:
        if _pwd_passlib.verify(password, stored_hash):
            return True
    except (ValueError, TypeError):
        pass
    
    return False

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['POST'])
def login_user():
    """
    Expect JSON: { "email": "...", "password": "..." }
    If credentials match, returns { token, refresh_token, user: { id, email, email_verified } }.
    """
    # Get client IP for security checks
    client_ip = get_client_ip()
    
    # Check if IP is blocked
    if is_ip_blocked(client_ip):
        return jsonify({"error": "Access denied. Your IP has been temporarily blocked due to too many failed attempts. Please try again later."}), 403
    
    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')

    if not email or not password:
        return jsonify({"error": "Please enter both your email and password to log in."}), 400

    user = User.query.filter_by(email=email).first()
    if not user:
        # Record failed attempt
        record_failed_login(client_ip, email)
        return jsonify({"error": "No account found with this email. Please check your email or register for a new account."}), 401

    # Check if user has journal access
    if not user.has_journal_access:
        return jsonify({
            "error": "You don't have access to the trading journal. Please contact support.",
            "action": "no_access"
        }), 403

    # Check if user is active
    if not user.is_active:
        return jsonify({"error": "Your account is disabled. Please contact support."}), 403

    pw_matches = verify_password_compat(user.password, password)

    if not pw_matches:
        # Record failed attempt
        record_failed_login(client_ip, email)
        return jsonify({"error": "Incorrect password. Please try again or reset your password if you've forgotten it."}), 401
    
    # Successful login - clear failed attempts for this IP
    clear_failed_attempts(client_ip)

    # Check if user has an active profile
    active_profile = Profile.query.filter_by(user_id=user.id, is_active=True).first()
    has_active_profile = active_profile is not None

    # Create both access and refresh tokens with admin claim
    access_token = create_access_token(
        identity=str(user.id),
        additional_claims={"is_admin": user.is_admin}
    )
    refresh_token = create_refresh_token(
        identity=str(user.id),
        additional_claims={"is_admin": user.is_admin}
    )

    return jsonify({
        "token": access_token,
        "refresh_token": refresh_token,
        "user": {
            "id": user.id,
            "email": user.email,
            "email_verified": True,
            "is_admin": user.is_admin,
            "has_active_profile": has_active_profile
        }
    }), 200


@auth_bp.route('/register', methods=['POST'])
def register_user():
    """
    Registration is disabled - users should register through the main platform.
    """
    return jsonify({"error": "Registration is disabled. Please register through the main platform at talaria-log.com"}), 403


@auth_bp.route('/verify-email', methods=['POST'])
def verify_email():
    """
    Expect JSON: { "code": "..." }
    Verifies user email with the provided 6-digit code.
    """
    data = request.get_json() or {}
    code = data.get('code', '').strip()

    if not code:
        return jsonify({"error": "Verification code is required"}), 400

    user = User.query.filter_by(verification_code=code).first()
    
    if not user:
        return jsonify({"error": "Invalid verification code"}), 400

    if user.is_verification_code_expired():
        return jsonify({"error": "Verification code has expired. Please request a new verification email."}), 400

    # Mark email as verified and clear code
    user.email_verified = True
    user.verification_code = None
    user.verification_code_expires = None
    
    db.session.commit()

    # Send welcome email after successful verification
    send_welcome_email(user)

    return jsonify({
        "message": "Email verified successfully! You can now log in to your account."
    }), 200


@auth_bp.route('/resend-verification', methods=['POST'])
def resend_verification():
    """
    Expect JSON: { "email": "..." }
    Resends verification email with new code to user.
    """
    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()

    if not email:
        return jsonify({"error": "Email is required"}), 400

    user = User.query.filter_by(email=email).first()
    
    if not user:
        return jsonify({"error": "User not found"}), 404

    if user.email_verified:
        return jsonify({"error": "Email is already verified"}), 400

    # Generate new verification code
    verification_code = user.generate_verification_code()
    db.session.commit()

    # Send verification email
    email_sent = send_verification_email(user, verification_code)
    
    if not email_sent:
        return jsonify({"error": "Failed to send verification email"}), 500

    return jsonify({
        "message": "Verification email sent successfully! Please check your inbox."
    }), 200


@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    """
    Expect JSON: { "email": "..." }
    Sends password reset email to user.
    """
    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()

    if not email:
        return jsonify({"error": "Email is required"}), 400

    user = User.query.filter_by(email=email).first()
    
    if not user:
        # Don't reveal if user exists or not for security
        return jsonify({
            "message": "If an account with this email exists, a password reset link has been sent."
        }), 200

    # Only send reset emails to verified email addresses to avoid bounces
    if not user.email_verified:
        current_app.logger.warning(f"Password reset requested for unverified email: {email}")
        return jsonify({
            "message": "If an account with this email exists, a password reset link has been sent."
        }), 200

    # Generate 6-digit reset code
    reset_code = user.generate_verification_token()
    db.session.commit()

    # Send password reset email with code
    email_sent = send_password_reset_email(user, reset_code)
    
    if not email_sent:
        return jsonify({"error": "Failed to send password reset email"}), 500

    return jsonify({
        "message": "تم إرسال رمز التحقق إلى بريدك الإلكتروني"
    }), 200


@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    """
    Expect JSON: { "email": "...", "code": "...", "new_password": "..." }
    Resets user password with the provided 6-digit code.
    """
    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()
    code = data.get('code', '').strip()
    new_password = data.get('new_password', '')

    if not email or not code or not new_password:
        return jsonify({"error": "البريد الإلكتروني والرمز وكلمة المرور الجديدة مطلوبة"}), 400

    if len(new_password) < 6:
        return jsonify({"error": "يجب أن تكون كلمة المرور 6 أحرف على الأقل"}), 400

    user = User.query.filter_by(email=email).first()
    
    if not user:
        return jsonify({"error": "رمز التحقق غير صحيح"}), 400

    if not user.verify_reset_token(code):
        return jsonify({"error": "رمز التحقق منتهي الصلاحية أو غير صحيح"}), 400

    # Update password and clear token
    user.password = generate_password_hash(new_password)
    user.clear_reset_token()
    
    db.session.commit()

    return jsonify({
        "message": "تم إعادة تعيين كلمة المرور بنجاح! يمكنك الآن تسجيل الدخول."
    }), 200


@auth_bp.route('/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    user_id_str = get_jwt_identity()
    user_id = int(user_id_str)
    data = request.get_json()
    user = User.query.get_or_404(user_id)

    if data.get('password'):
        user.password = generate_password_hash(data['password'])

    db.session.commit()
    return jsonify({
        'msg': 'Profile updated',
        'email': user.email
    }), 200


@auth_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    user_id_str = get_jwt_identity()
    user_id = int(user_id_str)
    user = User.query.get_or_404(user_id)
    return jsonify({
        'email': user.email,
        'name': user.name,
        'profile_image': ""
    }), 200


@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """Refresh access token"""
    current_user_id = get_jwt_identity()
    claims = get_jwt()
    new_access_token = create_access_token(
        identity=current_user_id,
        additional_claims={"is_admin": claims.get('is_admin', False)}
    )
    return jsonify({"token": new_access_token}), 200
    

@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """Logout user (client should remove tokens)"""
    return jsonify({"message": "Logged out successfully"}), 200


@auth_bp.route('/validate-token', methods=['POST'])
@jwt_required()
def validate_token():
    """
    Validate if the current token is still valid and return user info
    """
    try:
        user_id = get_jwt_identity()
        claims = get_jwt()
        
        # Check if user still exists
        user = User.query.get(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404
            
        return jsonify({
            "valid": True,
            "user": {
                "id": user.id,
                "email": user.email,
                "is_admin": user.is_admin,
                "email_verified": True
            }
        }), 200
    except Exception as e:
        current_app.logger.error(f"Token validation error: {str(e)}")
        return jsonify({"error": "Invalid token"}), 401


@auth_bp.route('/check-email-verified', methods=['POST'])
def check_email_verified():
    """
    Expect JSON: { "email": "..." }
    Returns { verified: true/false }
    """
    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()
    if not email:
        return jsonify({"error": "Email is required."}), 400
    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({"error": "No account found with this email."}), 404
    return jsonify({"verified": True, "has_journal_access": user.has_journal_access}), 200
