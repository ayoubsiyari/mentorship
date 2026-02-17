import secrets
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate, make_msgid
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import HTMLResponse
import uuid
import os
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


@router.get("/unsubscribe/{token}")
def unsubscribe_newsletter(
    token: str,
    db: Session = Depends(get_db)
):
    """Unsubscribe from the newsletter using the unique token."""
    from fastapi.responses import HTMLResponse
    
    subscriber = db.execute(
        select(NewsletterSubscriber).where(NewsletterSubscriber.unsubscribe_token == token)
    ).scalar_one_or_none()
    
    if not subscriber:
        return HTMLResponse(content=_get_unsubscribe_page(
            success=False,
            message="رابط إلغاء الاشتراك غير صالح",
            message_en="Invalid unsubscribe link"
        ), status_code=404)
    
    if not subscriber.is_active:
        return HTMLResponse(content=_get_unsubscribe_page(
            success=True,
            message="تم إلغاء اشتراكك مسبقاً",
            message_en="You have already unsubscribed"
        ))
    
    subscriber.is_active = False
    subscriber.unsubscribed_at = datetime.utcnow()
    db.commit()
    
    return HTMLResponse(content=_get_unsubscribe_page(
        success=True,
        message="تم إلغاء اشتراكك بنجاح من النشرة الإخبارية",
        message_en="You have been successfully unsubscribed"
    ))


def _get_unsubscribe_page(success: bool, message: str, message_en: str) -> str:
    """Generate HTML page for unsubscribe result."""
    icon = "✅" if success else "❌"
    bg_color = "#10b981" if success else "#ef4444"
    
    return f"""
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Talaria Newsletter - إلغاء الاشتراك</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{
                font-family: 'Inter', 'Segoe UI', Tahoma, sans-serif;
                background: linear-gradient(135deg, #030014 0%, #0a0a1a 50%, #1a1a2e 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 20px;
            }}
            .container {{
                max-width: 500px;
                width: 100%;
                background: rgba(15, 15, 35, 0.95);
                border-radius: 24px;
                padding: 48px 32px;
                text-align: center;
                border: 1px solid rgba(99, 102, 241, 0.2);
                box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
            }}
            .icon {{
                width: 80px;
                height: 80px;
                background: {bg_color};
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                margin: 0 auto 24px;
                font-size: 40px;
            }}
            .title {{
                color: #ffffff;
                font-size: 24px;
                font-weight: 700;
                margin-bottom: 16px;
            }}
            .message {{
                color: #c7d2fe;
                font-size: 18px;
                line-height: 1.6;
                margin-bottom: 12px;
            }}
            .message-en {{
                color: #9ca3af;
                font-size: 14px;
                margin-bottom: 32px;
            }}
            .logo {{
                margin-bottom: 32px;
            }}
            .logo img {{
                height: 60px;
                width: auto;
            }}
            .home-link {{
                display: inline-block;
                padding: 14px 32px;
                background: linear-gradient(135deg, #3b82f6, #6366f1);
                color: white;
                text-decoration: none;
                border-radius: 12px;
                font-weight: 600;
                transition: all 0.3s ease;
            }}
            .home-link:hover {{
                transform: translateY(-2px);
                box-shadow: 0 10px 20px rgba(99, 102, 241, 0.3);
            }}
            .thanks {{
                color: #6b7280;
                font-size: 13px;
                margin-top: 32px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="logo">
                <img src="https://talaria-log.com/logo-04.png" alt="Talaria">
            </div>
            <div class="icon">{icon}</div>
            <h1 class="title">النشرة الإخبارية</h1>
            <p class="message">{message}</p>
            <p class="message-en">{message_en}</p>
            <a href="https://talaria-log.com" class="home-link">العودة للموقع الرئيسي</a>
            <p class="thanks">شكراً لكونك جزءاً من مجتمع Talaria 💜</p>
        </div>
    </body>
    </html>
    """


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


UPLOAD_DIR = "/app/uploads/newsletter"

@router.post("/admin/upload-image")
async def upload_newsletter_image(
    file: UploadFile = File(...),
    admin: User = Depends(require_admin)
):
    """Upload an image for newsletter content (admin only)."""
    # Validate file type
    allowed_types = ["image/jpeg", "image/png", "image/gif", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Invalid file type. Only JPEG, PNG, GIF, WEBP allowed.")
    
    # Create upload directory if it doesn't exist
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    
    # Generate unique filename
    ext = file.filename.split('.')[-1] if '.' in file.filename else 'jpg'
    filename = f"{uuid.uuid4()}.{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)
    
    # Save file
    contents = await file.read()
    with open(filepath, "wb") as f:
        f.write(contents)
    
    # Return the URL
    return {"url": f"https://talaria-log.com/api/newsletter/images/{filename}"}


@router.get("/images/{filename}")
async def get_newsletter_image(filename: str):
    """Serve uploaded newsletter images."""
    from fastapi.responses import FileResponse
    filepath = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(filepath)


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
    display_name = name or "المتداول"
    unsubscribe_url = f"https://talaria-log.com/api/newsletter/unsubscribe/{unsubscribe_token}"
    
    html_body = f"""
    <!DOCTYPE html>
    <html dir="rtl" lang="ar">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{subject}</title>
    </head>
    <body style="margin: 0; padding: 0; background-color: #f5f5f5; font-family: 'Segoe UI', Tahoma, Arial, sans-serif;">
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #f5f5f5;">
            <tr>
                <td align="center" style="padding: 40px 20px;">
                    <table role="presentation" width="600" cellspacing="0" cellpadding="0" style="max-width: 600px; background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                        
                        <!-- HEADER - FIXED -->
                        <tr>
                            <td style="background-color: #ffffff; padding: 20px 30px 0;">
                                <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                                    <tr>
                                        <td width="60" style="text-align: left;"></td>
                                        <td style="text-align: center;">
                                            <img src="https://talaria-log.com/LOGO-09.png" alt="Talaria" style="height: 45px;">
                                        </td>
                                        <td width="60" style="text-align: right;">
                                            <a href="https://talaria-log.com/login" style="color: #1f2937; text-decoration: underline; font-size: 14px;">Login</a>
                                        </td>
                                    </tr>
                                </table>
                            </td>
                        </tr>
                        <tr>
                            <td style="padding: 0;">
                                <img src="https://talaria-log.com/logo-07.jpg?v=2" alt="Talaria Newsletter" style="width: 100%; height: auto; display: block; border-radius: 0;">
                            </td>
                        </tr>
                        
                        <!-- GREETING -->
                        <tr>
                            <td style="padding: 40px 40px 20px; direction: rtl; text-align: right;">
                                <p style="color: #1f2937; font-size: 16px; margin: 0; line-height: 1.6;">
                                    عزيزي <strong>{display_name}</strong>،
                                </p>
                            </td>
                        </tr>
                        
                        <!-- CONTENT - DYNAMIC -->
                        <tr>
                            <td style="padding: 0 40px 40px; direction: rtl; text-align: right;">
                                <div style="color: #374151; font-size: 15px; line-height: 1.8;">
                                    {content}
                                </div>
                            </td>
                        </tr>
                        
                        <!-- CTA BUTTON -->
                        <tr>
                            <td style="padding: 0 40px 40px; text-align: center;">
                                <a href="https://talaria-log.com" style="display: inline-block; background: linear-gradient(135deg, #3b82f6 0%, #6366f1 100%); color: #ffffff; text-decoration: none; padding: 14px 40px; border-radius: 8px; font-weight: 600; font-size: 14px;">
                                    تداول الآن
                                </a>
                            </td>
                        </tr>
                        
                        <!-- CONTACT SECTION - FIXED -->
                        <tr>
                            <td style="padding: 40px; background-color: #ffffff; text-align: center;">
                                <p style="color: #000000; font-size: 18px; margin: 0 0 25px; font-weight: 600;">هل لديك سؤال؟ تواصل معنا</p>
                                <table role="presentation" align="center" cellspacing="0" cellpadding="0">
                                    <tr>
                                        <td style="padding: 0 15px; text-align: center;">
                                            <a href="https://talaria-log.com" style="color: #60a5fa; text-decoration: none; font-size: 13px;">
                                                <img src="https://talaria-log.com/Icons-26.png?v=1" alt="Website" style="width: 50px; height: 50px; margin: 0 auto 8px; display: block;">
                                                الموقع
                                            </a>
                                        </td>
                                        <td style="padding: 0 15px; text-align: center;">
                                            <a href="mailto:support-center@talaria-log.com" style="color: #60a5fa; text-decoration: none; font-size: 13px;">
                                                <img src="https://talaria-log.com/Icons-27.png?v=1" alt="Email" style="width: 50px; height: 50px; margin: 0 auto 8px; display: block;">
                                                البريد
                                            </a>
                                        </td>
                                        <td style="padding: 0 15px; text-align: center;">
                                            <a href="https://talaria-log.com/journal" style="color: #60a5fa; text-decoration: none; font-size: 13px;">
                                                <img src="https://talaria-log.com/Icons-55.png?v=1" alt="Platform" style="width: 50px; height: 50px; margin: 0 auto 8px; display: block;">
                                                المنصة
                                            </a>
                                        </td>
                                    </tr>
                                </table>
                            </td>
                        </tr>

                        <!-- DISCLAIMER -->
                        <tr>
                            <td style="padding: 30px 40px; background-color: #f9fafb; border-top: 1px solid #e5e7eb;">
                                <p style="color: #6b7280; font-size: 12px; line-height: 1.6; margin: 0; font-style: italic; direction: rtl; text-align: right;">
                                    المواد المقدمة هنا لم يتم إعدادها وفقاً للمتطلبات القانونية المصممة لتعزيز استقلالية البحث الاستثماري، وعلى هذا النحو تعتبر رسالة تسويقية. Talaria لا تمثل أن المواد المقدمة هنا دقيقة أو حديثة أو كاملة، وبالتالي لا ينبغي الاعتماد عليها.
                                </p>
                            </td>
                        </tr>
                        
                        
                        
                        <!-- FOOTER - FIXED -->
                        <tr>
                            <td style="padding: 30px 40px; background-color: #0a1628; text-align: center;">
                                <!-- Social Links -->
                                <table role="presentation" align="center" cellspacing="0" cellpadding="0" style="margin-bottom: 20px;">
                                    <tr>
                                        <td style="padding: 0 8px;">
                                            <a href="https://twitter.com/talarialog" style="display: inline-block; width: 36px; height: 36px; background-color: rgba(255,255,255,0.1); border-radius: 50%; line-height: 36px; text-decoration: none;">
                                                <span style="color: #ffffff; font-size: 16px;">𝕏</span>
                                            </a>
                                        </td>
                                        <td style="padding: 0 8px;">
                                            <a href="https://instagram.com/talarialog" style="display: inline-block; width: 36px; height: 36px; background-color: rgba(255,255,255,0.1); border-radius: 50%; line-height: 36px; text-decoration: none;">
                                                <span style="color: #ffffff; font-size: 16px;">📷</span>
                                            </a>
                                        </td>
                                        <td style="padding: 0 8px;">
                                            <a href="https://youtube.com/@talarialog" style="display: inline-block; width: 36px; height: 36px; background-color: rgba(255,255,255,0.1); border-radius: 50%; line-height: 36px; text-decoration: none;">
                                                <span style="color: #ffffff; font-size: 16px;">▶️</span>
                                            </a>
                                        </td>
                                    </tr>
                                </table>
                                
                                <!-- Logo -->
                                <img src="https://talaria-log.com/logo-04.png" alt="Talaria" style="height: 35px; margin-bottom: 15px;">
                                
                                <!-- Links -->
                                <p style="margin: 0 0 15px;">
                                    <a href="https://talaria-log.com/privacy" style="color: #9ca3af; text-decoration: none; font-size: 12px;">سياسة الخصوصية</a>
                                    <span style="color: #4b5563; margin: 0 10px;">|</span>
                                    <a href="{unsubscribe_url}" style="color: #9ca3af; text-decoration: none; font-size: 12px;">إلغاء الاشتراك</a>
                                </p>
                                
                                <!-- Risk Warning -->
                                <p style="color: #6b7280; font-size: 11px; line-height: 1.5; margin: 0 0 15px; direction: rtl;">
                                    تحذير المخاطر: التداول في العقود مقابل الفروقات والفوركس محفوف بالمخاطر. قد تخسر أكثر من استثمارك الأولي. هذا البريد يحتوي على معلومات عامة ولا يأخذ في الاعتبار أهدافك الشخصية أو وضعك المالي.
                                </p>
                                
                                <!-- Copyright -->
                                <p style="color: #4b5563; font-size: 11px; margin: 0;">
                                    © 2026 Talaria Log Trading Platform. جميع الحقوق محفوظة.
                                </p>
                            </td>
                        </tr>
                        
                    </table>
                </td>
            </tr>
        </table>
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
