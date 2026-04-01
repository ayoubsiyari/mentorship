import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formatdate, make_msgid

from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import Session
from fastapi import Depends

from ..db import get_db
from ..deps import get_current_user
from ..models import BootcampRegistration, User
from ..schemas import BootcampRegisterIn
from ..settings import settings

logger = logging.getLogger(__name__)


def _send_registration_email(reg: BootcampRegistration) -> None:
    """Send email notification for new registration."""
    if not all([settings.smtp_host, settings.smtp_user, settings.smtp_password, settings.notification_email]):
        logger.info("Email settings not configured, skipping notification")
        return

    subject = f"New Mentorship Registration: {reg.full_name}"
    
    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; padding: 20px; background-color: #f5f5f5;">
        <div style="max-width: 600px; margin: 0 auto; background: white; border-radius: 10px; padding: 30px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
            <h2 style="color: #1a1a2e; border-bottom: 2px solid #4f46e5; padding-bottom: 10px;">🎓 New Mentorship Registration</h2>
            
            <table style="width: 100%; border-collapse: collapse; margin-top: 20px;">
                <tr style="background: #f8f9fa;">
                    <td style="padding: 12px; font-weight: bold; color: #666;">Name:</td>
                    <td style="padding: 12px; color: #1a1a2e;">{reg.full_name}</td>
                </tr>
                <tr>
                    <td style="padding: 12px; font-weight: bold; color: #666;">Email:</td>
                    <td style="padding: 12px; color: #1a1a2e;"><a href="mailto:{reg.email}">{reg.email}</a></td>
                </tr>
                <tr style="background: #f8f9fa;">
                    <td style="padding: 12px; font-weight: bold; color: #666;">Phone:</td>
                    <td style="padding: 12px; color: #1a1a2e;">{reg.phone or 'Not provided'}</td>
                </tr>
                <tr>
                    <td style="padding: 12px; font-weight: bold; color: #666;">Country:</td>
                    <td style="padding: 12px; color: #1a1a2e;">{reg.country}</td>
                </tr>
                <tr style="background: #f8f9fa;">
                    <td style="padding: 12px; font-weight: bold; color: #666;">Age:</td>
                    <td style="padding: 12px; color: #1a1a2e;">{reg.age}</td>
                </tr>
                <tr>
                    <td style="padding: 12px; font-weight: bold; color: #666;">Discord:</td>
                    <td style="padding: 12px; color: #1a1a2e;">{reg.discord}</td>
                </tr>
                <tr style="background: #f8f9fa;">
                    <td style="padding: 12px; font-weight: bold; color: #666;">Telegram:</td>
                    <td style="padding: 12px; color: #1a1a2e;">{reg.telegram or 'Not provided'}</td>
                </tr>
                <tr>
                    <td style="padding: 12px; font-weight: bold; color: #666;">Instagram:</td>
                    <td style="padding: 12px; color: #1a1a2e;">{reg.instagram or 'Not provided'}</td>
                </tr>
            </table>
            
            <p style="margin-top: 25px; padding: 15px; background: #e8f4f8; border-radius: 5px; color: #1a1a2e;">
                <strong>Reply directly to this email</strong> to contact the applicant at <a href="mailto:{reg.email}">{reg.email}</a>
            </p>
        </div>
    </body>
    </html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"Talaria <{settings.smtp_from_email or settings.smtp_user}>"
    msg["To"] = settings.notification_email
    msg["Reply-To"] = reg.email  # Allow replying directly to the applicant
    msg["Message-ID"] = make_msgid(domain="talaria-log.com")
    msg["Date"] = formatdate(localtime=True)

    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
        server.starttls()
        server.login(settings.smtp_user, settings.smtp_password)
        server.send_message(msg)


def _send_user_confirmation_email(reg: BootcampRegistration) -> None:
    """Send confirmation email to the user who registered."""
    if not all([settings.smtp_host, settings.smtp_user, settings.smtp_password]):
        logger.info("Email settings not configured, skipping user confirmation")
        return

    subject = "مرحباً بك في برنامج Talaria للمنتورشيب - تم تأكيد التسجيل"
    
    html_body = f"""
    <html dir="rtl">
    <body style="font-family: 'Segoe UI', Tahoma, Arial, sans-serif; padding: 20px; background-color: #1a1a2e; margin: 0;">
        <div style="max-width: 600px; margin: 0 auto; background-color: #0f0f23; border-radius: 15px; padding: 30px; border: 1px solid #3730a3; direction: rtl; text-align: right;">
            <div style="text-align: center; margin-bottom: 25px;">
                <h1 style="color: #ffffff; margin: 0; font-size: 28px;">🎓 Talaria Mentorship 2026</h1>
                <p style="color: #a5b4fc; margin-top: 5px;">تم تأكيد التسجيل</p>
            </div>
            
            <p style="color: #e0e7ff; font-size: 16px; line-height: 1.8;">
                عزيزي <strong style="color: #ffffff;">{reg.full_name}</strong>،
            </p>
            
            <p style="color: #c7d2fe; font-size: 15px; line-height: 1.8;">
                شكراً لتسجيلك في برنامج Talaria للمنتورشيب! تم استلام طلبك وهو قيد المراجعة.
            </p>
            
            <div style="background-color: #1e1b4b; border-radius: 10px; padding: 20px; margin: 25px 0; border: 1px solid #3730a3;">
                <h3 style="color: #a5b4fc; margin-top: 0; font-size: 16px;">تفاصيل التسجيل</h3>
                <table style="width: 100%; border-collapse: collapse; table-layout: fixed;">
                    <tr>
                        <td style="padding: 8px 0; color: #94a3b8; font-size: 14px; width: 80px;">الاسم:</td>
                        <td style="padding: 8px 0; color: #ffffff; font-size: 14px; word-break: break-word;"><strong>{reg.full_name}</strong></td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; color: #94a3b8; font-size: 14px;">البريد:</td>
                        <td style="padding: 8px 0; color: #60a5fa; font-size: 14px; direction: ltr; text-align: right; word-break: break-all;"><strong>{reg.email}</strong></td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; color: #94a3b8; font-size: 14px;">الهاتف:</td>
                        <td style="padding: 8px 0; color: #ffffff; font-size: 14px; direction: ltr; text-align: right;"><strong>{reg.phone or 'غير متوفر'}</strong></td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; color: #94a3b8; font-size: 14px;">الدولة:</td>
                        <td style="padding: 8px 0; color: #ffffff; font-size: 14px; word-break: break-word;"><strong>{reg.country}</strong></td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; color: #94a3b8; font-size: 14px;">Discord:</td>
                        <td style="padding: 8px 0; color: #ffffff; font-size: 14px; direction: ltr; text-align: right; word-break: break-all;"><strong>{reg.discord}</strong></td>
                    </tr>
                </table>
            </div>
            
            <div style="background-color: #422006; border-radius: 10px; padding: 20px; margin: 25px 0; border: 1px solid #ca8a04;">
                <h3 style="color: #fbbf24; margin-top: 0; font-size: 16px;">✅ الشروط والأحكام التي وافقت عليها</h3>
                <ul style="color: #fef3c7; font-size: 13px; line-height: 2; padding-right: 20px; margin: 0;">
                </ul>
                <div style="text-align: center; margin-top: 15px;">
                    <a href="https://talaria-log.com/files/mentorship-agreement.pdf" style="display: inline-block; background-color: #fbbf24; color: #422006; padding: 10px 20px; border-radius: 8px; font-size: 14px; font-weight: bold; text-decoration: none; margin-bottom: 10px;">📥 تحميل إقرار واتفاقية  (PDF)</a>
                </div>
                
            </div>
            
            <div style="background-color: #052e16; border-radius: 10px; padding: 20px; margin: 25px 0; border: 1px solid #16a34a;">
                <h3 style="color: #4ade80; margin-top: 0; font-size: 16px;">📌 ما التالي؟</h3>
                <p style="color: #bbf7d0; font-size: 14px; line-height: 1.8; margin: 0;">
                    سيقوم فريقنا بمراجعة طلبك والتواصل معك قريباً عبر البريد الإلكتروني مع تعليمات إضافية خلال 48h 
                </p>
            </div>
            
            <p style="color: #94a3b8; font-size: 13px; text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #3730a3;">
                إذا كان لديك أي أسئلة، رد على هذا البريد أو تواصل معنا على support-center@talaria-log.com
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
    msg["To"] = reg.email
    msg["Message-ID"] = make_msgid(domain="talaria-log.com")
    msg["Date"] = formatdate(localtime=True)

    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
        server.starttls()
        server.login(settings.smtp_user, settings.smtp_password)
        server.send_message(msg)


def _send_mentorship_acceptance_email(reg: BootcampRegistration) -> None:
    """Send mentorship acceptance email (same HTML as admin Email Templates → Mentorship Acceptance)."""
    if not all([settings.smtp_host, settings.smtp_user, settings.smtp_password]):
        logger.info("Email settings not configured, skipping mentorship acceptance email")
        return

    subject = "تهانينا! تم قبول طلبك للانضمام إلى برنامج المنتورشيب"

    # Kept in sync with journal-frontend BulkEmailManager EMAIL_TEMPLATES id=mentorship-acceptance
    html_body = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; background-color: #f5f5f5; font-family: 'Segoe UI', Tahoma, Arial, sans-serif; direction: rtl; text-align: right;">
    <table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="background-color: #f5f5f5; direction: rtl;">
        <tr>
            <td align="center" style="padding: 20px 10px;">
                <table role="presentation" cellpadding="0" cellspacing="0" style="max-width: 600px; width: 100%; background-color: #ffffff; border-radius: 12px; overflow: hidden; direction: rtl; text-align: right;">
                    <tr>
                        <td style="background-color: #1e3a5f; padding: 30px 20px; text-align: center;">
                            <img src="https://talaria-log.com/logo-08.png" alt="Talaria" width="100" style="display: block; margin: 0 auto; max-width: 100px;">
                            <h1 style="color: #ffffff; font-size: 24px; margin: 20px 0 0 0; font-weight: 700;">🎉 تهانينا!</h1>
                            <p style="color: #ffffff; font-size: 14px; margin: 10px 0 0 0;">تم قبول طلبك للانضمام</p>
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 20px; direction: rtl; text-align: right;">
                            <table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="margin-bottom: 25px;">
                                <tr>
                                    <td style="background-color: #e8f4fd; border-right: 4px solid #1e3a5f; padding: 15px; border-radius: 6px;">
                                        <p style="color: #000000; font-size: 14px; margin: 0; line-height: 1.6;">⚠️ لضمان مكانك في المنتورشيب يرجى اتباع الخطوات التالية:</p>
                                    </td>
                                </tr>
                            </table>
                            <table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="margin-bottom: 25px;">
                                <tr>
                                    <td style="background-color: #f8f9fa; border-radius: 8px; padding: 20px; border: 1px solid #e0e0e0;">
                                        <h3 style="color: #1e3a5f; font-size: 14px; margin: 0 0 12px 0; font-weight: 700;">📋 قبل البدء</h3>
                                        <ul style="color: #000000; font-size: 14px; line-height: 1.8; margin: 0; padding-right: 20px; padding-left: 0;">
                                            <li>يرجى سداد رسوم المنتورشيب <strong>خلال سبعة أيام</strong> من استلام هذه الرسالة، وإلا سيتم إلغاء الحجز.</li>
                                            <li>الرسوم <strong>غير قابلة للاسترداد</strong> إلا في حالة إلغاء المنتورشيب.</li>
                                            <li>تبدأ الدروس الساعة <strong>9 مساءً بتوقيت مكة المكرمة</strong> من الاثنين إلى الجمعة.</li>
                                        </ul>
                                    </td>
                                </tr>
                            </table>
                            <table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="margin-bottom: 25px;">
                                <tr>
                                    <td style="background-color: #f8f9fa; border-radius: 8px; padding: 20px; border: 1px solid #e0e0e0;">
                                        <h3 style="color: #1e3a5f; font-size: 14px; margin: 0 0 12px 0; font-weight: 700;">1️⃣ التواصل عبر ديسكورد</h3>
                                        <p style="color: #000000; font-size: 14px; line-height: 1.6; margin: 0 0 10px 0;">التواصل في المنتورشيب يتم عبر تطبيق <strong>ديسكورد</strong></p>
                                        <ul style="color: #000000; font-size: 14px; line-height: 1.8; margin: 0; padding-right: 20px; padding-left: 0;">
                                            <li>إذا كان لديك حساب ديسكورد، أرسل اسم المستخدم الخاص بك.</li>
                                            <li>إذا لم يكن لديك حساب، قم بتحميل البرنامج من <a href="https://discord.com" style="color: #1e3a5f; font-weight: 600;">discord.com</a></li>
                                        </ul>
                                    </td>
                                </tr>
                            </table>
                            <table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="margin-bottom: 25px;">
                                <tr>
                                    <td style="background-color: #f8f9fa; border-radius: 8px; padding: 20px; border: 1px solid #e0e0e0;">
                                        <h3 style="color: #1e3a5f; font-size: 14px; margin: 0 0 12px 0; font-weight: 700;">2️⃣ إتمام عملية الدفع</h3>
                                        <p style="color: #e30909; font-size: 11px; margin: 8px 0 12px 0; padding: 0 12px; text-align: center;">⚠️ تأكد من نسخ العنوان بشكل صحيح وكامل</p>
                                        <p style="color: #cc0000; font-size: 15px; margin: 8px 0 12px 0; padding: 0 12px; text-align: center;">للمزيد من طرق الدفع يرجى التواصل مع (support-center@talaria-log.com)</p>
                                                <table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="background-color: #ffffff; border: 1px solid #e0e0e0; border-radius: 6px;">
                                            <tr><td style="padding: 12px; border-bottom: 1px solid #e0e0e0;"><span style="color: #000000; font-size: 14px;">طريقة الدفع: <strong>الكريبتو</strong></span></td></tr>
                                            <tr><td style="padding: 12px; border-bottom: 1px solid #e0e0e0;"><span style="color: #000000; font-size: 14px;">نوع العملة: <strong>USDC أو USDT</strong></span></td></tr>
                                            <tr><td style="padding: 12px; border-bottom: 1px solid #e0e0e0;"><span style="color: #000000; font-size: 14px;">المبلغ: <strong style="color: #1e3a5f;">$700</strong></span></td></tr>
                                            <tr><td style="padding: 12px; border-bottom: 1px solid #e0e0e0;"><span style="color: #000000; font-size: 14px;">الشبكة: <strong>BEP20</strong></span></td></tr>
                                            <tr>
                                                <td style="padding: 0;">
                                                    <p style="color: #000000; font-size: 12px; margin: 0 0 8px 0; padding: 0 12px;">عنوان المحفظة:</p>
                                                    <div style="background-color: #e8e8e8; padding: 12px 2px; text-align: center; margin: 0; width: 100%;">
                                                        <span style="font-size: 7px; color: #000000; font-family: Arial, sans-serif; letter-spacing: -0.3px;">0xe25D96504c2106a243dc93D948d19640Cf6F4800</span>
                                                    </div>
                                                    <p style="color: #cc0000; font-size: 11px; margin: 8px 0 12px 0; padding: 0 12px; text-align: center;">⚠️ تأكد من نسخ العنوان بشكل صحيح وكامل</p>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>
                            <table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="margin-bottom: 25px;">
                                <tr>
                                    <td style="background-color: #f8f9fa; border-radius: 8px; padding: 20px; border: 1px solid #e0e0e0;">
                                        <h3 style="color: #1e3a5f; font-size: 14px; margin: 0 0 12px 0; font-weight: 700;">3️⃣ عند إتمام الدفع</h3>
                                        <p style="color: #000000; font-size: 14px; line-height: 1.6; margin: 0 0 12px 0;">عند قيامك باتمام عملية الدفع، قم بإرسال المعلومات أدناه لنا عبر بريدنا الالكتروني:<br><strong style="color: #1e3a5f;">support-center@talaria-log.com</strong><br>متضمناً:</p>
                                        <ul style="color: #000000; font-size: 14px; line-height: 1.8; margin: 0; padding-right: 20px; padding-left: 0;">
                                            <li><strong>1.</strong> اسم معرف الديسكورد (USER NAME)</li>
                                            <li><strong>2.</strong> كود عملية التحويل (TXID) - <strong>لن يتم قبول طلبك بدونه</strong></li>
                                        </ul>
                                    </td>
                                </tr>
                            </table>
                            <table role="presentation" cellpadding="0" cellspacing="0" width="100%">
                                <tr>
                                    <td style="background-color: #1e3a5f; border-radius: 8px; padding: 20px; text-align: center;">
                                        <p style="color: #ffffff; font-size: 14px; line-height: 1.6; margin: 0;">✅ بعد استلام المبلغ ستتلقى رسالة تأكيد،<br>تليها تفاصيل الدخول إلى سيرفر الديسكورد بين <strong>٣ و ٥ يوليو</strong></p>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    <tr>
                        <td style="background-color: #f8f9fa; padding: 25px; text-align: center; border-top: 1px solid #e0e0e0;">
                            <p style="color: #000000; font-size: 14px; margin: 0 0 8px 0;">للاستفسارات، تواصل معنا عبر</p>
                            <a href="mailto:support-center@talaria-log.com" style="color: #1e3a5f; font-size: 14px; font-weight: 600;">support-center@talaria-log.com</a>
                            <p style="color: #000000; font-size: 14px; margin: 15px 0 0 0;">© 2026 Talaria-Log <br>جميع الحقوق محفوظة</p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"Talaria <{settings.smtp_from_email or settings.smtp_user}>"
    msg["To"] = reg.email
    msg["Message-ID"] = make_msgid(domain="talaria-log.com")
    msg["Date"] = formatdate(localtime=True)

    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
        server.starttls()
        server.login(settings.smtp_user, settings.smtp_password)
        server.send_message(msg)


def _append_registration_to_google_sheets(reg: BootcampRegistration) -> None:
    if not settings.google_sheets_spreadsheet_id:
        return
    if not settings.google_service_account_file:
        return

    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build

    creds = Credentials.from_service_account_file(
        settings.google_service_account_file,
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )
    service = build("sheets", "v4", credentials=creds, cache_discovery=False)
    values = [
        [
            (reg.created_at.isoformat() if getattr(reg, "created_at", None) else ""),
            reg.full_name,
            reg.email,
            reg.phone or "",
            reg.country,
            reg.age,
            reg.telegram or "",
            reg.discord,
            reg.instagram or "",
            reg.agree_terms,
            reg.agree_rules,
        ]
    ]
    service.spreadsheets().values().append(
        spreadsheetId=settings.google_sheets_spreadsheet_id,
        range=f"{settings.google_sheets_sheet_name}!A1",
        valueInputOption="RAW",
        insertDataOption="INSERT_ROWS",
        body={"values": values},
    ).execute()

router = APIRouter(prefix="/api/bootcamp", tags=["bootcamp"])


@router.get("/registrations/emails")
def get_registration_emails(
    db: Session = Depends(get_db),
):
    """Get all bootcamp registration emails for bulk email filtering."""
    registrations = db.query(BootcampRegistration.email).all()
    return {
        "emails": [r.email.lower() for r in registrations],
        "count": len(registrations)
    }


@router.get("/registrations")
def get_registrations(
    db: Session = Depends(get_db),
):
    """Get all bootcamp registrations with details."""
    registrations = db.query(BootcampRegistration).order_by(BootcampRegistration.created_at.desc()).all()
    return {
        "registrations": [
            {
                "id": r.id,
                "full_name": r.full_name,
                "email": r.email,
                "phone": r.phone,
                "country": r.country,
                "age": r.age,
                "discord": r.discord,
                "telegram": r.telegram,
                "instagram": r.instagram,
                "created_at": r.created_at.isoformat() if r.created_at else None
            }
            for r in registrations
        ],
        "count": len(registrations)
    }


@router.post("/register")
def register(
    payload: BootcampRegisterIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not payload.agree_terms or not payload.agree_rules:
        raise HTTPException(status_code=400, detail="Terms and rules must be accepted")
    if payload.age < 18:
        raise HTTPException(status_code=400, detail="Must be 18 or older")

    reg = BootcampRegistration(
        full_name=(user.name or "").strip() or payload.full_name.strip(),
        email=(user.email or "").lower() or str(payload.email).lower(),
        phone=(payload.phone.strip() if payload.phone else None),
        country=payload.country.strip(),
        age=int(payload.age),
        telegram=(payload.telegram.strip() if payload.telegram else None),
        discord=payload.discord.strip(),
        instagram=(payload.instagram.strip() if payload.instagram else None),
        agree_terms=bool(payload.agree_terms),
        agree_rules=bool(payload.agree_rules),
    )
    db.add(reg)
    
    # Also save phone and country to user profile
    if payload.phone and payload.phone.strip():
        user.phone = payload.phone.strip()
    if payload.country and payload.country.strip():
        user.country = payload.country.strip()
    
    db.commit()
    db.refresh(reg)
    try:
        _append_registration_to_google_sheets(reg)
    except Exception:
        logger.exception("google_sheets_append_failed")
    try:
        _send_registration_email(reg)
    except Exception:
        logger.exception("email_notification_failed")
    try:
        _send_user_confirmation_email(reg)
    except Exception:
        logger.exception("user_confirmation_email_failed")
    try:
        _send_mentorship_acceptance_email(reg)
    except Exception:
        logger.exception("mentorship_acceptance_email_failed")
    return {"ok": True, "id": reg.id}
