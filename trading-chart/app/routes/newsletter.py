import secrets
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate, make_msgid
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import require_admin
from app.models import NewsletterSubscriber, User
from app.email_validator import validate_email
from app.settings import settings

router = APIRouter(prefix="/api/newsletter", tags=["newsletter"])


class SubscribeRequest(BaseModel):
    email: EmailStr
    name: str | None = None
    source: str | None = "homepage"


class SubscribeResponse(BaseModel):
    success: bool
    message: str


class UnsubscribeResponse(BaseModel):
    success: bool
    message: str


@router.post("/subscribe", response_model=SubscribeResponse)
def subscribe_newsletter(
    data: SubscribeRequest,
    db: Session = Depends(get_db)
):
    """Subscribe to the newsletter."""
    email = data.email.lower().strip()
    
    # Validate email
    is_valid, message, corrected = validate_email(email, check_api=False)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message or "البريد الإلكتروني غير صالح"
        )
    
    # Use corrected email if available
    if corrected:
        email = corrected
    
    # Check if already subscribed
    existing = db.execute(
        select(NewsletterSubscriber).where(NewsletterSubscriber.email == email)
    ).scalar_one_or_none()
    
    if existing:
        if existing.is_active:
            return SubscribeResponse(
                success=True,
                message="أنت مشترك بالفعل في النشرة الإخبارية"  # Already subscribed
            )
        else:
            # Reactivate subscription
            existing.is_active = True
            existing.unsubscribed_at = None
            existing.subscribed_at = datetime.utcnow()
            db.commit()
            return SubscribeResponse(
                success=True,
                message="تم إعادة تفعيل اشتراكك بنجاح"  # Subscription reactivated
            )
    
    # Create new subscriber
    unsubscribe_token = secrets.token_urlsafe(32)
    subscriber = NewsletterSubscriber(
        email=email,
        name=data.name,
        source=data.source,
        unsubscribe_token=unsubscribe_token,
        is_active=True
    )
    db.add(subscriber)
    db.commit()
    
    return SubscribeResponse(
        success=True,
        message="تم الاشتراك بنجاح في النشرة الإخبارية"  # Successfully subscribed
    )


@router.get("/unsubscribe/{token}", response_model=UnsubscribeResponse)
def unsubscribe_newsletter(
    token: str,
    db: Session = Depends(get_db)
):
    """Unsubscribe from the newsletter using the unique token."""
    subscriber = db.execute(
        select(NewsletterSubscriber).where(NewsletterSubscriber.unsubscribe_token == token)
    ).scalar_one_or_none()
    
    if not subscriber:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="رابط إلغاء الاشتراك غير صالح"  # Invalid unsubscribe link
        )
    
    if not subscriber.is_active:
        return UnsubscribeResponse(
            success=True,
            message="تم إلغاء اشتراكك مسبقاً"  # Already unsubscribed
        )
    
    subscriber.is_active = False
    subscriber.unsubscribed_at = datetime.utcnow()
    db.commit()
    
    return UnsubscribeResponse(
        success=True,
        message="تم إلغاء اشتراكك بنجاح من النشرة الإخبارية"  # Successfully unsubscribed
    )


# ==================== ADMIN ENDPOINTS ====================

class SubscriberOut(BaseModel):
    id: int
    email: str
    name: str | None
    is_active: bool
    subscribed_at: datetime
    unsubscribed_at: datetime | None
    source: str | None

    class Config:
        from_attributes = True


class SubscribersListResponse(BaseModel):
    subscribers: list[SubscriberOut]
    total: int
    active_count: int


class SendNewsletterRequest(BaseModel):
    subject: str
    content: str  # HTML content
    send_to_all: bool = True
    subscriber_ids: list[int] | None = None


class SendNewsletterResponse(BaseModel):
    success: bool
    sent_count: int
    failed_count: int
    message: str


@router.get("/admin/subscribers", response_model=SubscribersListResponse)
def list_subscribers(
    active_only: bool = False,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """List all newsletter subscribers (admin only)."""
    query = select(NewsletterSubscriber)
    if active_only:
        query = query.where(NewsletterSubscriber.is_active == True)
    
    query = query.order_by(NewsletterSubscriber.subscribed_at.desc())
    subscribers = db.execute(query).scalars().all()
    
    # Get counts
    total = len(subscribers)
    active_count = sum(1 for s in subscribers if s.is_active)
    
    return SubscribersListResponse(
        subscribers=[SubscriberOut.model_validate(s) for s in subscribers],
        total=total,
        active_count=active_count
    )


@router.post("/admin/send", response_model=SendNewsletterResponse)
def send_newsletter(
    data: SendNewsletterRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """Send newsletter to subscribers (admin only)."""
    # Get subscribers to send to
    if data.send_to_all:
        subscribers = db.execute(
            select(NewsletterSubscriber).where(NewsletterSubscriber.is_active == True)
        ).scalars().all()
    elif data.subscriber_ids:
        subscribers = db.execute(
            select(NewsletterSubscriber).where(
                NewsletterSubscriber.id.in_(data.subscriber_ids),
                NewsletterSubscriber.is_active == True
            )
        ).scalars().all()
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="يجب تحديد المشتركين أو اختيار إرسال للجميع"
        )
    
    if not subscribers:
        return SendNewsletterResponse(
            success=True,
            sent_count=0,
            failed_count=0,
            message="لا يوجد مشتركين نشطين لإرسال النشرة إليهم"
        )
    
    sent_count = 0
    failed_count = 0
    
    for subscriber in subscribers:
        try:
            _send_newsletter_email(
                email=subscriber.email,
                name=subscriber.name,
                subject=data.subject,
                content=data.content,
                unsubscribe_token=subscriber.unsubscribe_token
            )
            sent_count += 1
        except Exception as e:
            print(f"Failed to send newsletter to {subscriber.email}: {e}")
            failed_count += 1
    
    return SendNewsletterResponse(
        success=True,
        sent_count=sent_count,
        failed_count=failed_count,
        message=f"تم إرسال النشرة إلى {sent_count} مشترك بنجاح"
    )


@router.delete("/admin/subscribers/{subscriber_id}")
def delete_subscriber(
    subscriber_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """Delete a subscriber (admin only)."""
    subscriber = db.get(NewsletterSubscriber, subscriber_id)
    if not subscriber:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="المشترك غير موجود"
        )
    
    db.delete(subscriber)
    db.commit()
    
    return {"success": True, "message": "تم حذف المشترك بنجاح"}


def _send_newsletter_email(
    email: str,
    name: str | None,
    subject: str,
    content: str,
    unsubscribe_token: str
) -> None:
    """Send newsletter email to a subscriber."""
    display_name = name or "عزيزي المشترك"
    unsubscribe_url = f"https://talaria-log.com/api/newsletter/unsubscribe/{unsubscribe_token}"
    
    html_body = f"""
    <html dir="rtl">
    <body style="font-family: 'Segoe UI', Tahoma, Arial, sans-serif; padding: 20px; background-color: #1a1a2e; margin: 0;">
        <div style="max-width: 600px; margin: 0 auto; background-color: #0f0f23; border-radius: 15px; padding: 30px; border: 1px solid #3730a3; direction: rtl; text-align: right;">
            <div style="text-align: center; margin-bottom: 25px;">
                <h1 style="color: #ffffff; margin: 0; font-size: 28px;">📬 Talaria Newsletter</h1>
            </div>
            
            <p style="color: #e0e7ff; font-size: 16px; line-height: 1.8;">
                مرحباً <strong style="color: #ffffff;">{display_name}</strong>،
            </p>
            
            <div style="color: #c7d2fe; font-size: 15px; line-height: 1.8;">
                {content}
            </div>
            
            <hr style="border: none; border-top: 1px solid #3730a3; margin: 30px 0;">
            
            <p style="color: #6b7280; font-size: 12px; text-align: center;">
                لإلغاء الاشتراك من النشرة الإخبارية، 
                <a href="{unsubscribe_url}" style="color: #60a5fa;">اضغط هنا</a>
            </p>
            
            <p style="color: #4b5563; font-size: 11px; text-align: center; margin-top: 20px;">
                © 2026 Talaria Log Trading Platform
            </p>
        </div>
    </body>
    </html>
    """
    
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"Talaria Newsletter <{settings.smtp_from_email}>"
    msg["To"] = email
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid(domain="talaria-log.com")
    
    msg.attach(MIMEText(html_body, "html", "utf-8"))
    
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
        server.starttls()
        server.login(settings.smtp_user, settings.smtp_password)
        server.sendmail(settings.smtp_from_email, email, msg.as_string())
