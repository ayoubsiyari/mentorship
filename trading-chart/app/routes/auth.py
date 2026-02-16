import logging
import random
import smtplib
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..deps import get_current_user
from ..db import get_db
from ..models import User
from ..schemas import LoginIn, SignupIn, UpdateProfileIn, UserPublic, VerifyEmailIn, ResendCodeIn, ForgotPasswordIn, ResetPasswordIn
from ..security import create_session_token, hash_password, verify_password
from ..settings import settings
from ..email_validator import validate_email, check_domain_typo, is_blocked_domain

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])


def generate_verification_code() -> str:
    """Generate a 6-digit verification code."""
    return str(random.randint(100000, 999999))


def send_verification_email(email: str, code: str, name: str) -> None:
    """Send verification code email to user."""
    if not all([settings.smtp_host, settings.smtp_user, settings.smtp_password]):
        logger.warning("SMTP not configured, skipping verification email")
        return

    subject = f"رمز التحقق من Talaria: {code}"
    
    html_body = f"""
    <html dir="rtl">
    <body style="font-family: 'Segoe UI', Tahoma, Arial, sans-serif; padding: 20px; background-color: #1a1a2e; margin: 0;">
        <div style="max-width: 600px; margin: 0 auto; background-color: #0f0f23; border-radius: 15px; padding: 30px; border: 1px solid #3730a3; direction: rtl; text-align: right;">
            <div style="text-align: center; margin-bottom: 25px;">
                <h1 style="color: #ffffff; margin: 0; font-size: 28px;">🎓 Talaria</h1>
                <p style="color: #a5b4fc; margin-top: 5px;">التحقق من البريد الإلكتروني</p>
            </div>
            
            <p style="color: #e0e7ff; font-size: 16px; line-height: 1.8;">
                مرحباً <strong style="color: #ffffff;">{name}</strong>،
            </p>
            
            <p style="color: #c7d2fe; font-size: 15px; line-height: 1.8;">
                شكراً لتسجيلك! يرجى استخدام رمز التحقق أدناه لإكمال التسجيل:
            </p>
            
            <div style="background-color: #1e1b4b; border-radius: 10px; padding: 30px; margin: 25px 0; border: 1px solid #3730a3; text-align: center;">
                <p style="color: #94a3b8; font-size: 14px; margin: 0 0 10px 0;">رمز التحقق الخاص بك:</p>
                <h2 style="color: #60a5fa; font-size: 32px; letter-spacing: 6px; margin: 0; font-family: monospace; direction: ltr; white-space: nowrap;">{code}</h2>
            </div>
            
            <p style="color: #fbbf24; font-size: 14px; line-height: 1.8;">
                  <strong>ستنتهي صلاحية هذا الرمز خلال ١٠ دقائق </strong>
            </p>
            
            <div style="background-color: #1e1b4b; border-radius: 10px; padding: 15px; margin: 20px 0; border: 1px solid #3730a3; text-align: center;">
                <p style="color: #94a3b8; font-size: 13px; margin: 0 0 10px 0;">لقراءة الشروط والأحكام:</p>
                <a href="https://talaria-log.com/terms" style="color: #60a5fa; font-size: 14px; text-decoration: none;">https://talaria-log.com/terms</a>
            </div>
            
            <p style="color: #94a3b8; font-size: 13px; text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #3730a3;">
                إذا لم تقم بإنشاء حساب، يمكنك تجاهل هذا البريد الإلكتروني.
            </p>
            
            <p style="color: #64748b; font-size: 12px; text-align: center; margin-top: 15px;">
                © 2026 Talaria-Log. جميع الحقوق محفوظة.
            </p>
        </div>
    </body>
    </html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"Talaria <{settings.smtp_from_email or settings.smtp_user}>"
    msg["To"] = email

    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
        server.starttls()
        server.login(settings.smtp_user, settings.smtp_password)
        server.send_message(msg)


def send_password_reset_email(email: str, code: str, name: str) -> None:
    """Send password reset code email to user."""
    if not all([settings.smtp_host, settings.smtp_user, settings.smtp_password]):
        logger.warning("SMTP not configured, skipping password reset email")
        return

    subject = f"رمز إعادة تعيين كلمة المرور من Talaria: {code}"
    
    html_body = f"""
    <html dir="rtl">
    <body style="font-family: 'Segoe UI', Tahoma, Arial, sans-serif; padding: 20px; background-color: #1a1a2e; margin: 0;">
        <div style="max-width: 600px; margin: 0 auto; background-color: #0f0f23; border-radius: 15px; padding: 30px; border: 1px solid #3730a3; direction: rtl; text-align: right;">
            <div style="text-align: center; margin-bottom: 25px;">
                <h1 style="color: #ffffff; margin: 0; font-size: 28px;">🔐 Talaria</h1>
                <p style="color: #a5b4fc; margin-top: 5px;">إعادة تعيين كلمة المرور</p>
            </div>
            
            <p style="color: #e0e7ff; font-size: 16px; line-height: 1.8;">
                مرحباً <strong style="color: #ffffff;">{name}</strong>،
            </p>
            
            <p style="color: #c7d2fe; font-size: 15px; line-height: 1.8;">
                لقد تلقينا طلباً لإعادة تعيين كلمة المرور الخاصة بك. استخدم الرمز أدناه لتعيين كلمة مرور جديدة:
            </p>
            
            <div style="background-color: #1e1b4b; border-radius: 10px; padding: 30px; margin: 25px 0; border: 1px solid #3730a3; text-align: center;">
                <p style="color: #94a3b8; font-size: 14px; margin: 0 0 10px 0;">رمز إعادة التعيين:</p>
                <h2 style="color: #f87171; font-size: 32px; letter-spacing: 6px; margin: 0; font-family: monospace; direction: ltr; white-space: nowrap;">{code}</h2>
            </div>
            
            <p style="color: #fbbf24; font-size: 14px; line-height: 1.8;">
                ⚠️ سينتهي هذا الرمز خلال <strong>10 دقائق</strong>.
            </p>
            
            <div style="background-color: #1e1b4b; border-radius: 10px; padding: 15px; margin: 20px 0; border: 1px solid #3730a3; text-align: center;">
                <p style="color: #94a3b8; font-size: 13px; margin: 0 0 10px 0;">لقراءة الشروط والأحكام:</p>
                <a href="https://talaria-log.com/terms" style="color: #60a5fa; font-size: 14px; text-decoration: none;">https://talaria-log.com/terms</a>
            </div>
            
            <p style="color: #94a3b8; font-size: 13px; text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #3730a3;">
                إذا لم تطلب إعادة تعيين كلمة المرور، يمكنك تجاهل هذا البريد الإلكتروني.
            </p>
            
            <p style="color: #64748b; font-size: 12px; text-align: center; margin-top: 15px;">
                © 2026 Talaria-Log. جميع الحقوق محفوظة.
            </p>
        </div>
    </body>
    </html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"Talaria <{settings.smtp_from_email or settings.smtp_user}>"
    msg["To"] = email

    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
        server.starttls()
        server.login(settings.smtp_user, settings.smtp_password)
        server.send_message(msg)


@router.post("/signup")
def signup(payload: SignupIn, db: Session = Depends(get_db)):
    # Validate email format and check for typos/blocked domains
    email = payload.email.strip().lower()
    is_valid, message, suggested_email = validate_email(email, check_api=True)
    
    if not is_valid:
        raise HTTPException(status_code=400, detail=message)
    
    # If there's a suggested correction (typo detected), return suggestion
    if suggested_email and suggested_email != email:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid email domain. {message}"
        )
    
    existing = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    
    if existing:
        if existing.email_verified:
            raise HTTPException(status_code=400, detail="Email already registered")
        else:
            # User exists but not verified - resend code
            code = generate_verification_code()
            existing.verification_code = code
            existing.verification_code_expires = datetime.utcnow() + timedelta(minutes=10)
            existing.name = payload.name.strip()
            existing.password_hash = hash_password(payload.password)
            existing.phone = payload.phone.strip() if payload.phone else None
            existing.country = payload.country.strip() if payload.country else None
            db.commit()
            
            try:
                send_verification_email(existing.email, code, existing.name)
            except Exception:
                logger.exception("Failed to send verification email")
            
            return {"message": "Verification code sent", "email": existing.email, "requires_verification": True}

    code = generate_verification_code()
    user = User(
        name=payload.name.strip(),
        email=email,
        password_hash=hash_password(payload.password),
        role="user",
        is_active=False,  # Not active until verified
        email_verified=False,
        verification_code=code,
        verification_code_expires=datetime.utcnow() + timedelta(minutes=10),
        phone=payload.phone.strip() if payload.phone else None,
        country=payload.country.strip() if payload.country else None,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    try:
        send_verification_email(user.email, code, user.name)
    except Exception:
        logger.exception("Failed to send verification email")

    return {"message": "Verification code sent", "email": user.email, "requires_verification": True}


@router.post("/verify-email")
def verify_email(payload: VerifyEmailIn, response: Response, db: Session = Depends(get_db)):
    user = db.execute(select(User).where(User.email == payload.email.lower())).scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=400, detail="User not found")
    
    if user.email_verified:
        raise HTTPException(status_code=400, detail="Email already verified")
    
    if not user.verification_code:
        raise HTTPException(status_code=400, detail="No verification code found. Please sign up again.")
    
    if user.verification_code_expires and datetime.utcnow() > user.verification_code_expires:
        raise HTTPException(status_code=400, detail="Verification code expired. Please request a new one.")
    
    if user.verification_code != payload.code:
        raise HTTPException(status_code=400, detail="Invalid verification code")
    
    # Verify the user
    user.email_verified = True
    user.is_active = True
    user.verification_code = None
    user.verification_code_expires = None
    db.commit()
    db.refresh(user)
    
    # Create session
    token = create_session_token(user.id)
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        httponly=True,
        secure=bool(settings.session_cookie_secure),
        samesite=settings.session_cookie_samesite,
        path="/",
    )
    
    return {"user": UserPublic.model_validate(user, from_attributes=True), "message": "Email verified successfully"}


@router.post("/resend-code")
def resend_code(payload: ResendCodeIn, db: Session = Depends(get_db)):
    user = db.execute(select(User).where(User.email == payload.email.lower())).scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=400, detail="User not found")
    
    if user.email_verified:
        raise HTTPException(status_code=400, detail="Email already verified")
    
    code = generate_verification_code()
    user.verification_code = code
    user.verification_code_expires = datetime.utcnow() + timedelta(minutes=10)
    db.commit()
    
    try:
        send_verification_email(user.email, code, user.name)
    except Exception:
        logger.exception("Failed to send verification email")
        raise HTTPException(status_code=500, detail="Failed to send verification email")
    
    return {"message": "Verification code sent", "email": user.email}


@router.post("/login")
def login(payload: LoginIn, response: Response, db: Session = Depends(get_db)):
    user = db.execute(select(User).where(User.email == payload.email.lower())).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not user.email_verified:
        raise HTTPException(status_code=403, detail="Email not verified", headers={"X-Requires-Verification": "true"})
    
    if not user.is_active:
        raise HTTPException(status_code=401, detail="Account is deactivated")
    
    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_session_token(user.id)
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        httponly=True,
        secure=bool(settings.session_cookie_secure),
        samesite=settings.session_cookie_samesite,
        path="/",
    )

    return {"user": UserPublic.model_validate(user, from_attributes=True)}


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(key=settings.session_cookie_name, path="/")
    return {"ok": True}


@router.get("/me")
def me(response: Response, user: User = Depends(get_current_user)):
    response.headers["Cache-Control"] = "no-store"
    response.headers["Vary"] = "Cookie"
    return {"user": UserPublic.model_validate(user, from_attributes=True)}


@router.put("/update-profile")
def update_profile(payload: UpdateProfileIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if payload.name is not None:
        user.name = payload.name.strip()
    if payload.phone is not None:
        user.phone = payload.phone.strip() if payload.phone else None
    if payload.country is not None:
        user.country = payload.country.strip() if payload.country else None
    db.commit()
    db.refresh(user)
    return {"user": UserPublic.model_validate(user, from_attributes=True)}


@router.post("/forgot-password")
def forgot_password(payload: ForgotPasswordIn, db: Session = Depends(get_db)):
    user = db.execute(select(User).where(User.email == payload.email.lower())).scalar_one_or_none()
    
    # Always return success to prevent email enumeration
    if not user:
        return {"message": "If an account exists, a reset code has been sent"}
    
    if not user.email_verified:
        return {"message": "If an account exists, a reset code has been sent"}
    
    code = generate_verification_code()
    user.reset_code = code
    user.reset_code_expires = datetime.utcnow() + timedelta(minutes=10)
    db.commit()
    
    try:
        send_password_reset_email(user.email, code, user.name)
    except Exception:
        logger.exception("Failed to send password reset email")
    
    return {"message": "If an account exists, a reset code has been sent", "email": payload.email.lower()}


@router.post("/reset-password")
def reset_password(payload: ResetPasswordIn, db: Session = Depends(get_db)):
    user = db.execute(select(User).where(User.email == payload.email.lower())).scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=400, detail="Invalid reset request")
    
    if not user.reset_code:
        raise HTTPException(status_code=400, detail="No reset code found. Please request a new one.")
    
    if user.reset_code_expires and datetime.utcnow() > user.reset_code_expires:
        raise HTTPException(status_code=400, detail="Reset code expired. Please request a new one.")
    
    if user.reset_code != payload.code:
        raise HTTPException(status_code=400, detail="Invalid reset code")
    
    # Update password
    user.password_hash = hash_password(payload.new_password)
    user.reset_code = None
    user.reset_code_expires = None
    db.commit()
    
    return {"message": "Password reset successfully"}
