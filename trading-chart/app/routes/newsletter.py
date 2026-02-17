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
    
    # Check if user exists in our database
    user = db.execute(
        select(User).where(User.email == email)
    ).scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="يجب عليك التسجيل أولاً للاشتراك في النشرة الإخبارية"  # You must sign up first
        )
    
    # Check if already subscribed to newsletter
    existing = db.execute(
        select(NewsletterSubscriber).where(NewsletterSubscriber.email == email)
    ).scalar_one_or_none()
    
    if existing:
        if existing.is_active:
            return SubscribeResponse(
                success=False,
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
        name=data.name or user.name,
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
    test_email: str | None = None  # Send test to specific email


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
MAX_IMAGE_SIZE = 1200  # Max width/height in pixels
MAX_FILE_SIZE_KB = 200  # Target max file size

def compress_image(image_bytes: bytes, max_size: int = MAX_IMAGE_SIZE, quality: int = 85) -> bytes:
    """Compress and resize image to optimize for email."""
    from PIL import Image
    import io
    
    img = Image.open(io.BytesIO(image_bytes))
    
    # Convert RGBA to RGB if needed (for JPEG)
    if img.mode in ('RGBA', 'P'):
        background = Image.new('RGB', img.size, (255, 255, 255))
        if img.mode == 'P':
            img = img.convert('RGBA')
        background.paste(img, mask=img.split()[3] if len(img.split()) > 3 else None)
        img = background
    
    # Resize if too large
    if img.width > max_size or img.height > max_size:
        img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
    
    # Save with compression
    output = io.BytesIO()
    img.save(output, format='JPEG', quality=quality, optimize=True)
    
    # If still too large, reduce quality
    while output.tell() > MAX_FILE_SIZE_KB * 1024 and quality > 40:
        quality -= 10
        output = io.BytesIO()
        img.save(output, format='JPEG', quality=quality, optimize=True)
    
    return output.getvalue()


@router.post("/admin/upload-image")
async def upload_newsletter_image(
    file: UploadFile = File(...),
    admin: User = Depends(require_admin)
):
    """Upload an image for newsletter content (admin only). Auto-compresses for email."""
    # Validate file type
    allowed_types = ["image/jpeg", "image/png", "image/gif", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Invalid file type. Only JPEG, PNG, GIF, WEBP allowed.")
    
    # Create upload directory if it doesn't exist
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    
    # Read and compress image
    contents = await file.read()
    original_size = len(contents)
    
    # Compress image (always save as JPEG for consistency)
    compressed = compress_image(contents)
    compressed_size = len(compressed)
    
    # Generate unique filename (always .jpg after compression)
    filename = f"{uuid.uuid4()}.jpg"
    filepath = os.path.join(UPLOAD_DIR, filename)
    
    # Save compressed file
    with open(filepath, "wb") as f:
        f.write(compressed)
    
    # Return the URL with compression stats
    return {
        "url": f"https://talaria-log.com/api/newsletter/images/{filename}",
        "filename": filename,
        "original_size_kb": round(original_size / 1024, 1),
        "compressed_size_kb": round(compressed_size / 1024, 1)
    }


@router.get("/admin/gallery")
async def list_newsletter_images(admin: User = Depends(require_admin)):
    """List all uploaded newsletter images for gallery."""
    if not os.path.exists(UPLOAD_DIR):
        return {"images": []}
    
    images = []
    for filename in os.listdir(UPLOAD_DIR):
        if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
            filepath = os.path.join(UPLOAD_DIR, filename)
            stat = os.stat(filepath)
            images.append({
                "filename": filename,
                "url": f"https://talaria-log.com/api/newsletter/images/{filename}",
                "size_kb": round(stat.st_size / 1024, 1),
                "created_at": stat.st_mtime
            })
    
    # Sort by creation time, newest first
    images.sort(key=lambda x: x["created_at"], reverse=True)
    return {"images": images}


@router.delete("/admin/gallery/{filename}")
async def delete_newsletter_image(filename: str, admin: User = Depends(require_admin)):
    """Delete an uploaded newsletter image."""
    filepath = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Image not found")
    
    os.remove(filepath)
    return {"success": True, "message": "Image deleted"}


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
    sent_count = 0
    failed_count = 0
    
    # Test email mode - send to single email
    if data.test_email:
        try:
            _send_newsletter_email(
                email=data.test_email,
                name="Test User",
                subject=f"[TEST] {data.subject}",
                content=data.content,
                unsubscribe_token="test-token"
            )
            return SendNewsletterResponse(
                success=True,
                sent_count=1,
                failed_count=0,
                message=f"تم إرسال البريد التجريبي إلى {data.test_email}"
            )
        except Exception as e:
            return SendNewsletterResponse(
                success=False,
                sent_count=0,
                failed_count=1,
                message=f"فشل إرسال البريد التجريبي: {str(e)}"
            )
    
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
<body style="margin: 0; padding: 0; background-color: #f0f2f5; font-family: 'Segoe UI', Tahoma, Arial, sans-serif;">

<!-- Hidden preview text -->
<div style="display:none; max-height:0; overflow:hidden;">{subject} — Talaria &nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;</div>

<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #f0f2f5;">
    <tr>
        <td align="center" style="padding: 48px 16px;">

            <table role="presentation" width="620" cellspacing="0" cellpadding="0" style="max-width: 620px; width: 100%;">

                <!-- ── TOP LABEL ── -->
                <tr>
                    <td style="padding-bottom: 20px; text-align: center;">
                        <p style="margin: 0; font-size: 10px; letter-spacing: 3.5px; color: #8a95a3; text-transform: uppercase;">
                            TALARIA &nbsp;&middot;&nbsp; WEEKLY NEWSLETTER
                        </p>
                    </td>
                </tr>

                <!-- ── MAIN CARD ── -->
                <tr>
                    <td style="background-color: #ffffff; border-radius: 4px; overflow: hidden; box-shadow: 0 2px 12px rgba(0,0,0,0.08);">
                        <table role="presentation" width="100%" cellspacing="0" cellpadding="0">

                            <!-- ── HEADER NAV ── -->
                            <tr>
                                <td style="padding: 22px 36px; border-bottom: 2px solid #0057ff;">
                                    <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                                        <tr>
                                            <td style="text-align: right; vertical-align: middle;">
                                                <a href="https://talaria-log.com/login" style="color: #0057ff; text-decoration: none; font-size: 12px; letter-spacing: 1px; font-weight: 600; text-transform: uppercase;">تسجيل الدخول</a>
                                            </td>
                                            <td style="text-align: center; vertical-align: middle;">
                                                <!-- PRESERVED -->
                                                <img src="https://talaria-log.com/LOGO-09.png" alt="Talaria" style="height: 38px; display: inline-block;">
                                            </td>
                                            <td width="80"></td>
                                        </tr>
                                    </table>
                                </td>
                            </tr>

                            <!-- ── HERO IMAGE ── -->
                            <tr>
                                <td style="padding: 0; line-height: 0;">
                                    <!-- PRESERVED -->
                                    <img src="https://talaria-log.com/logo-07.jpg?v=2" alt="Talaria Newsletter" style="width: 100%; height: auto; display: block;">
                                </td>
                            </tr>

                            <!-- ── BLUE ACCENT RULE ── -->
                            <tr>
                                <td style="padding: 0; line-height: 0;">
                                    <div style="height: 3px; background-color: #0057ff;"></div>
                                </td>
                            </tr>

                            <!-- ── GREETING ── -->
                            <tr>
                                <td style="padding: 44px 40px 12px; direction: rtl; text-align: right;">
                                    <p style="margin: 0; font-size: 17px; color: #0a0a0a; line-height: 1.6;">
                                        عزيزي <strong>{display_name}</strong>،
                                    </p>
                                </td>
                            </tr>

                            <!-- ── CONTENT ── -->
                            <tr>
                                <td style="padding: 16px 40px 44px; direction: rtl; text-align: right;">
                                    <div style="color: #2c2c2c; font-size: 15px; line-height: 2;">
                                        {content}
                                    </div>
                                </td>
                            </tr>

                            <!-- ── DIVIDER ── -->
                            <tr>
                                <td style="padding: 0 40px;">
                                    <div style="height: 1px; background-color: #e4e8ed;"></div>
                                </td>
                            </tr>

                            <!-- ── CTA ── -->
                            <tr>
                                <td style="padding: 40px; text-align: center;">
                                    <a href="https://talaria-log.com" style="display: inline-block; background-color: #0057ff; color: #ffffff; text-decoration: none; padding: 15px 52px; font-size: 14px; font-weight: 700; letter-spacing: 1px; text-transform: uppercase; border-radius: 2px;">
                                        تداول الآن
                                    </a>
                                </td>
                            </tr>

                            <!-- ── DIVIDER ── -->
                            <tr>
                                <td style="padding: 0 40px;">
                                    <div style="height: 1px; background-color: #e4e8ed;"></div>
                                </td>
                            </tr>

                            <!-- ── CONTACT ── -->
                            <tr>
                                <td style="padding: 40px; text-align: center;">
                                    <p style="margin: 0 0 28px; font-size: 13px; color: #0a0a0a; font-weight: 700; letter-spacing: 2px; text-transform: uppercase;">هل لديك سؤال؟ تواصل معنا</p>
                                    <table role="presentation" align="center" cellspacing="0" cellpadding="0">
                                        <tr>
                                            <td style="padding: 0 20px; text-align: center;">
                                                <a href="https://talaria-log.com" style="text-decoration: none;">
                                                    <!-- PRESERVED -->
                                                    <img src="https://talaria-log.com/Icons-26.png?v=1" alt="Website" style="width: 46px; height: 46px; display: block; margin: 0 auto 10px;">
                                                    <span style="color: #0057ff; font-size: 12px; font-weight: 600;">الموقع</span>
                                                </a>
                                            </td>
                                            <td style="padding: 0 20px; text-align: center;">
                                                <a href="mailto:support-center@talaria-log.com" style="text-decoration: none;">
                                                    <!-- PRESERVED -->
                                                    <img src="https://talaria-log.com/Icons-27.png?v=1" alt="Email" style="width: 46px; height: 46px; display: block; margin: 0 auto 10px;">
                                                    <span style="color: #0057ff; font-size: 12px; font-weight: 600;">البريد</span>
                                                </a>
                                            </td>
                                            <td style="padding: 0 20px; text-align: center;">
                                                <a href="https://talaria-log.com/journal" style="text-decoration: none;">
                                                    <!-- PRESERVED -->
                                                    <img src="https://talaria-log.com/Icons-55.png?v=1" alt="Platform" style="width: 46px; height: 46px; display: block; margin: 0 auto 10px;">
                                                    <span style="color: #0057ff; font-size: 12px; font-weight: 600;">المنصة</span>
                                                </a>
                                            </td>
                                        </tr>
                                    </table>
                                </td>
                            </tr>

                            <!-- ── DISCLAIMER ── -->
                            <tr>
                                <td style="padding: 24px 40px; background-color: #f7f8fa; border-top: 1px solid #e4e8ed;">
                                    <p style="margin: 0; color: #8a95a3; font-size: 11px; line-height: 1.8; direction: rtl; text-align: right; font-style: italic;">
                                        المواد المقدمة هنا لم يتم إعدادها وفقاً للمتطلبات القانونية المصممة لتعزيز استقلالية البحث الاستثماري، وعلى هذا النحو تعتبر رسالة تسويقية. Talaria لا تمثل أن المواد المقدمة هنا دقيقة أو حديثة أو كاملة، وبالتالي لا ينبغي الاعتماد عليها.
                                    </p>
                                </td>
                            </tr>

                            <!-- ── FOOTER ── -->
                            <tr>
                                <td style="padding: 32px 40px; background-color: #0a0a0a; text-align: center;">

                                    <!-- Social -->
                                    <table role="presentation" align="center" cellspacing="0" cellpadding="0" style="margin-bottom: 22px;">
                                        <tr>
                                            <td style="padding: 0 6px;">
                                                <a href="https://twitter.com/talarialog" style="display: inline-block; width: 36px; height: 36px; border: 1px solid #2a2a2a; border-radius: 50%; line-height: 36px; text-decoration: none; text-align: center;">
                                                    <span style="color: #ffffff; font-size: 14px;">𝕏</span>
                                                </a>
                                            </td>
                                            <td style="padding: 0 6px;">
                                                <a href="https://instagram.com/talarialog" style="display: inline-block; width: 36px; height: 36px; border: 1px solid #2a2a2a; border-radius: 50%; line-height: 36px; text-decoration: none; text-align: center;">
                                                    <span style="color: #ffffff; font-size: 14px;">📷</span>
                                                </a>
                                            </td>
                                            <td style="padding: 0 6px;">
                                                <a href="https://youtube.com/@talarialog" style="display: inline-block; width: 36px; height: 36px; border: 1px solid #2a2a2a; border-radius: 50%; line-height: 36px; text-decoration: none; text-align: center;">
                                                    <span style="color: #ffffff; font-size: 14px;">▶️</span>
                                                </a>
                                            </td>
                                        </tr>
                                    </table>

                                    <!-- PRESERVED: Footer logo -->
                                    <img src="https://talaria-log.com/logo-04.png" alt="Talaria" style="height: 30px; display: block; margin: 0 auto 20px; opacity: 0.85;">

                                    <!-- Footer links -->
                                    <p style="margin: 0 0 14px;">
                                        <a href="https://talaria-log.com/privacy" style="color: #555; text-decoration: none; font-size: 11px; letter-spacing: 0.5px;">سياسة الخصوصية</a>
                                        <span style="color: #2a2a2a; margin: 0 10px;">|</span>
                                        <!-- PRESERVED -->
                                        <a href="{unsubscribe_url}" style="color: #555; text-decoration: none; font-size: 11px; letter-spacing: 0.5px;">إلغاء الاشتراك</a>
                                    </p>

                                    <!-- Risk warning -->
                                    <p style="color: #3a3a3a; font-size: 10px; line-height: 1.7; margin: 0 0 14px; direction: rtl; max-width: 480px; margin-left: auto; margin-right: auto;">
                                        تحذير المخاطر: التداول في العقود مقابل الفروقات والفوركس محفوف بالمخاطر. قد تخسر أكثر من استثمارك الأولي. هذا البريد يحتوي على معلومات عامة ولا يأخذ في الاعتبار أهدافك الشخصية أو وضعك المالي.
                                    </p>

                                    <!-- Copyright -->
                                    <p style="color: #2a2a2a; font-size: 10px; margin: 0; letter-spacing: 0.5px;">
                                        © 2026 Talaria Log Trading Platform &nbsp;·&nbsp; جميع الحقوق محفوظة
                                    </p>

                                </td>
                            </tr>

                        </table>
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
