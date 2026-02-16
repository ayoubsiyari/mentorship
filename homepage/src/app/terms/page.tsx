"use client";
import React from "react";
import { motion } from "framer-motion";
import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import Image from "next/image";
import { Button } from "@/components/ui/button";
import SiteDisclosuresFooter from "@/components/SiteDisclosuresFooter";

export default function TermsPage() {
  const copy = React.useMemo(
    () => ({
      ar: {
            backHome: "العودة للرئيسية",
            title: "شروط الخدمة",
            updated: "آخر تحديث: يناير 2026",
            sections: {
              s1t: "1. قبول الشروط",
              s1p:
                "من خلال الوصول إلى Talaria Log (\"المنصة\") واستخدامها، فإنك توافق على الالتزام بهذه الشروط. إذا لم توافق، يرجى عدم استخدام خدماتنا.",
              s2t: "2. وصف الخدمة",
              s2p:
                "توفر Talaria Log أدوات تحليل للتداول، وبرمجيات رسوم بيانية، وقدرات اختبار خلفي، وموارد تعليمية. صُممت منصتنا لأغراض معلوماتية وتعليمية فقط.",
              s3t: "3. حسابات المستخدمين",
              s3p: "عند إنشاء حساب، فإنك توافق على:",
              s3l: [
                "تقديم معلومات دقيقة وكاملة",
                "الحفاظ على أمان بيانات الدخول",
                "تحمل المسؤولية عن جميع الأنشطة التي تتم عبر حسابك",
                "إبلاغنا فوراً بأي وصول غير مصرح به",
              ],
              s4t: "4. الاستخدام المقبول",
              s4p: "أنت توافق على عدم القيام بـ:",
              s4l: [
                "استخدام المنصة لأي غرض غير قانوني",
                "محاولة الوصول غير المصرح به إلى أنظمتنا",
                "التدخل أو تعطيل تشغيل المنصة",
                "مشاركة بيانات حسابك مع الآخرين",
                "الهندسة العكسية أو نسخ تقنيتنا الخاصة",
              ],
              s5t: "5. الملكية الفكرية",
              s5p:
                "جميع المحتويات والميزات والوظائف في المنصة، بما في ذلك النصوص والرسومات والشعارات والبرمجيات، هي ملكية حصرية لـ Talaria Log ومحميّة بموجب قوانين حقوق النشر والعلامات التجارية وغيرها.",
              s6t: "6. تحديد المسؤولية",
              s6p:
                "لن تكون Talaria Log مسؤولة عن أي أضرار غير مباشرة أو عرضية أو خاصة أو تبعية أو عقابية ناتجة عن استخدامك للمنصة. ولن تتجاوز مسؤوليتنا الإجمالية المبلغ الذي دفعته خلال الاثني عشر شهراً السابقة للمطالبة.",
              s7t: "7. الإنهاء",
              s7p:
                "نحتفظ بالحق في إنهاء أو تعليق حسابك في أي وقت ودون إشعار مسبق إذا اعتبرنا أن سلوكك يخالف هذه الشروط أو يضر بالمستخدمين الآخرين أو بنا أو بطرف ثالث.",
              s8t: "8. تغييرات على الشروط",
              s8p:
                "نحتفظ بالحق في تعديل هذه الشروط في أي وقت. سنقوم بإبلاغ المستخدمين بأي تغييرات جوهرية عبر البريد الإلكتروني أو من خلال المنصة. استمرارك في الاستخدام بعد التغييرات يعني قبولك.",
              s9t: "9. تواصل معنا",
              s9p: "للاستفسارات حول شروط الخدمة، تواصل معنا على:",
            },
            footer: "© 2026 Talaria Log Trading Platform. جميع الحقوق محفوظة.",
          },
      en: {
            backHome: "Back Home",
            title: "Terms of Service",
            updated: "Last updated: January 2026",
            sections: {
              s1t: "1. Acceptance of Terms",
              s1p:
                "By accessing and using Talaria Log (\"the Platform\"), you agree to be bound by these Terms of Service. If you do not agree to these terms, please do not use our services.",
              s2t: "2. Description of Service",
              s2p:
                "Talaria Log provides trading analysis tools, charting software, backtesting capabilities, and educational resources. Our platform is designed for informational and educational purposes only.",
              s3t: "3. User Accounts",
              s3p: "When creating an account, you agree to:",
              s3l: [
                "Provide accurate and complete information",
                "Maintain the security of your account credentials",
                "Accept responsibility for all activities under your account",
                "Notify us immediately of any unauthorized access",
              ],
              s4t: "4. Acceptable Use",
              s4p: "You agree not to:",
              s4l: [
                "Use the platform for any unlawful purpose",
                "Attempt to gain unauthorized access to our systems",
                "Interfere with or disrupt the platform's operation",
                "Share your account credentials with others",
                "Reverse engineer or copy our proprietary technology",
              ],
              s5t: "5. Intellectual Property",
              s5p:
                "All content, features, and functionality of the Platform, including but not limited to text, graphics, logos, and software, are the exclusive property of Talaria Log and are protected by copyright, trademark, and other intellectual property laws.",
              s6t: "6. Limitation of Liability",
              s6p:
                "Talaria Log shall not be liable for any indirect, incidental, special, consequential, or punitive damages resulting from your use of the platform. Our total liability shall not exceed the amount you paid us in the twelve months prior to the claim.",
              s7t: "7. Termination",
              s7p:
                "We reserve the right to terminate or suspend your account at any time, without prior notice, for conduct that we believe violates these Terms of Service or is harmful to other users, us, or third parties.",
              s8t: "8. Changes to Terms",
              s8p:
                "We reserve the right to modify these terms at any time. We will notify users of any material changes via email or through the Platform. Continued use of the service after changes constitutes acceptance.",
              s9t: "9. Contact Us",
              s9p:
                "For questions about these Terms of Service, contact us at:",
            },
            footer: "© 2026 Talaria Log Trading Platform. All rights reserved.",
          },
    }),
    []
  );

  const LegalContent = ({ t, dir }: { t: any; dir: "ltr" | "rtl" }) => (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6 }}
      dir={dir}
      className={dir === "rtl" ? "text-right" : "text-left"}
    >
      <h1 className="text-4xl font-bold text-white mb-8">{t.title}</h1>
      <p className="text-neutral-400 mb-4">{t.updated}</p>

      <div className="prose prose-invert max-w-none space-y-8">
        <section>
          <h2 className="text-2xl font-semibold text-white mb-4">{t.sections.s1t}</h2>
          <p className="text-neutral-300 leading-relaxed">{t.sections.s1p}</p>
        </section>

        <section>
          <h2 className="text-2xl font-semibold text-white mb-4">{t.sections.s2t}</h2>
          <p className="text-neutral-300 leading-relaxed">{t.sections.s2p}</p>
        </section>

        <section>
          <h2 className="text-2xl font-semibold text-white mb-4">{t.sections.s3t}</h2>
          <p className="text-neutral-300 leading-relaxed mb-4">{t.sections.s3p}</p>
          <ul className="list-disc list-inside text-neutral-300 space-y-2">
            {t.sections.s3l.map((item: string) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </section>

        <section>
          <h2 className="text-2xl font-semibold text-white mb-4">{t.sections.s4t}</h2>
          <p className="text-neutral-300 leading-relaxed mb-4">{t.sections.s4p}</p>
          <ul className="list-disc list-inside text-neutral-300 space-y-2">
            {t.sections.s4l.map((item: string) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </section>

        <section>
          <h2 className="text-2xl font-semibold text-white mb-4">{t.sections.s5t}</h2>
          <p className="text-neutral-300 leading-relaxed">{t.sections.s5p}</p>
        </section>

        <section>
          <h2 className="text-2xl font-semibold text-white mb-4">{t.sections.s6t}</h2>
          <p className="text-neutral-300 leading-relaxed">{t.sections.s6p}</p>
        </section>

        <section>
          <h2 className="text-2xl font-semibold text-white mb-4">{t.sections.s7t}</h2>
          <p className="text-neutral-300 leading-relaxed">{t.sections.s7p}</p>
        </section>

        <section>
          <h2 className="text-2xl font-semibold text-white mb-4">{t.sections.s8t}</h2>
          <p className="text-neutral-300 leading-relaxed">{t.sections.s8p}</p>
        </section>

        <section>
          <h2 className="text-2xl font-semibold text-white mb-4">{t.sections.s9t}</h2>
          <p className="text-neutral-300 leading-relaxed">{t.sections.s9p}</p>
          <p className="text-blue-400 mt-2">
            <a href="mailto:support-center@talaria-log.com">support-center@talaria-log.com</a>
          </p>
        </section>
      </div>
    </motion.div>
  );

  return (
    <main className="min-h-screen bg-[#030014]">
      {/* Navigation */}
      <nav className="relative z-50 px-6 py-4 border-b border-white/5">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2">
            <Image src="/logo-04.png" alt="Talaria" width={40} height={40} className="h-10 w-10" />
            <span className="text-2xl font-bold text-white">Talaria Log</span>
          </Link>
          <Link href="/">
            <Button variant="ghost" className="text-white hover:text-blue-400">
              <ArrowLeft className="w-4 h-4 mr-2" />
              {copy.en.backHome}
            </Button>
          </Link>
        </div>
      </nav>

      {/* Content */}
      <div className="max-w-4xl mx-auto px-6 py-16">
        <LegalContent t={copy.en} dir="ltr" />
        <div className="my-14 h-px bg-white/10" />
        <LegalContent t={copy.ar} dir="rtl" />
      </div>

      <SiteDisclosuresFooter />
    </main>
  );
}
