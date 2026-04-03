"use client";
import React from "react";
import { Button } from "@/components/ui/button";
import { GlowEffect } from "@/components/ui/glow-effect";
import SiteDisclosuresFooter from "@/components/SiteDisclosuresFooter";
import { motion } from "framer-motion";
import {
  BookOpen,
  Target,
  Trophy,
  ChevronDown,
  ArrowLeft,
  PlayCircle,
  CheckCircle,
} from "lucide-react";
import Link from "next/link";
import Image from "next/image";
import HermesLogo from "../../../Hermes-Logofix2-600x734.webp";
import { useLanguage } from "../LanguageProvider";

import NinjaTraderWordmark from "../../../ninjatrader/Landing-Page-Text-Images/NinjaTrader/NinjaTrader_Wordmark_color_RGB.png";

const talariaBrands = [
  // Add more brands as needed
  { name: "Talaria-Prop", href: "#" },
  { name: "Talaria-Flow", href: "#" },
  { name: "Talaria-Copy", href: "#" },
];

const bootcampModules = [
  {
    title: "Module 1: Important statistical concepts for trading",
    description: "",
    details: [
      "How to formulate a robust, clearly-defined trading strategy.",
      "How to run backtests and validate your strategy with real numbers using Talaria.",
      "Using statistics and risk metrics to improve and elevate your performance.",
    ],
    lessons: 5,
    duration: "15 hours",
    status: "available",
  },
  {
    title: "Module 2: How to read fundamental economics",
    description: "",
    details: [
      "How to apply fundamentals in a practical way in your day-to-day trading.",
      "Making decisions and planning trades based on economic factors.",
      "Understanding different market regimes and how to adapt to them.",
    ],
    lessons: 5,
    duration: "15 hours",
    status: "available",
  },
  {
    title: "Module 3: Statistical based Technical analysis concepts",
    description: "",
    details: [
      "Evidence-based, statistics-driven technical analysis concepts (away from randomness).",
      "Generating ideas for multiple strategies and high-probability technical concepts.",
      "The importance of trade journaling and the right way to do it with Talaria.",
    ],
    lessons: 5,
    duration: "15 hours",
    status: "available",
  },
  {
    title: "Module 4: Risk management & trading strategies",
    description: "",
    details: [
      "Understanding position sizing and how to use it effectively.",
      "Risk management fundamentals and how to handle prop firms and personal accounts efficiently.",
      "Execution roadmap: transitioning from strict rule-based trading to discretionary trading.",
    ],
    lessons: 5,
    duration: "15 hours",
    status: "available",
  },
];

const bootcampModulesAr = [
  {
    title: "الجزء 1: مفاهيم إحصائية جوهرية في التداول",
    description: "",
    details: [
      "كيفية صياغة استراتيجية تداول محكمة وواضحة المعالم.",
      "كيفية إجراء الاختبار الخلفي (Backtesting) والتحقق من كفاءة استراتيجيتك بالأرقام الحقيقية باستخدام تالاريا.",
      "استغلال الإحصائيات ومقاييس المخاطر لتحسين ورفع مستوى أدائك.",
    ],
    lessons: 5,
    duration: "15 ساعة",
    status: "available",
  },
  {
    title: "الجزء 2:  كيفية قراءة وفهم الاقتصاد والتحليل الأساسي",
    description: "",
    details: [
      "كيفية توظيف التحليل الأساسي (Fundamentals) بشكل عملي في تداولك اليومي.",
      "بناء قرارات وتخطيط الصفقات استناداً إلى العوامل الاقتصادية.",
      "فهم واستيعاب أنظمة السوق  (Market Regimes) المختلفة والتعامل معها.",
    ],
    lessons: 5,
    duration: "15 ساعة",
    status: "available",
  },
  {
    title: "الجزء 3: مفاهيم التحليل الفني القائمة على الإحصاء",
    description: "",
    details: [
      "مفاهيم التحليل الفني المبنية على الإحصاء والأدلة (بعيداً عن العشوائية).",
      "الحصول على أفكار لاستراتيجيات متعددة ومفاهيم فنية ذات احتمالية نجاح عالية.",
      "أهمية تدوين الصفقات (Journaling) والطريقة الصحيحة لتطبيقه بالاستعانة ب تالاريا.",
    ],
    lessons: 5,
    duration: "15 ساعة",
    status: "available",
  },
  {
    title: "الجزء 4: إدارة المخاطر واستراتيجيات التداول",
    description: "",
    details: [
      "فهم حجم المركز (Position Sizing) وكيفية استخدامه بفعالية.",
      "أساسيات إدارة المخاطر وكيفية التعامل مع شركات التمويل و الحسابات الشخصية بكفاءة.",
      "خارطة طريق للتنفيذ: الانتقال من التداول القائم على القواعد الصارمة إلى التداول التقديري",
    ],
    lessons: 5,
    duration: "15 ساعة",
    status: "available",
  },
];

export default function BootcampPage() {
  const { isArabic } = useLanguage();
  const [joinMenuOpen, setJoinMenuOpen] = React.useState(false);
  const [joinMenuLoading, setJoinMenuLoading] = React.useState(false);

  const handleJoinNow = async () => {
    setJoinMenuLoading(true);
    try {
      const res = await fetch("/api/auth/me", { credentials: "include", cache: "no-store" });
      const data = await res.json().catch(() => null);
      const authed = Boolean(res.ok && data && (data as any).user && typeof (data as any).user.id === "number");
      if (authed) {
        window.location.href = "/register/";
        return;
      }
      setJoinMenuOpen(true);
    } catch {
      setJoinMenuOpen(true);
    } finally {
      setJoinMenuLoading(false);
    }
  };
  const t = React.useMemo(
    () =>
      isArabic
        ? {
            nav: { backHome: "العودة للرئيسية" },
            tabs: { bootcamp: "المنتورشيب", soon: "قريباً" },
            header: {
              a: "",
              b: "المنتورشيب",
              subtitle:
                "طور تداولك من خلال المنتورشيب وتعلم من الأساسيات حتى  الاستراتيجيات المتقدمة",
              joinNow: "انضم الآن",
            },
            stats: {
              modules: "أجزاء",
              sessions: " محاضرة",
              hours: "ساعه",
              tools: "بأدوات Talaria-Log ",
              toolsValue: "اشتراك شهرين",
            },
            module: {
              details: "",
              lessons: "دروس",
              comingSoon: "قريباً",
            },
            disclosures: {
              riskTitle: "إفصاح المخاطر:",
              riskText:
                "تداول العقود الآجلة والفوركس ينطوي على مخاطر كبيرة وقد تخسر كامل أو أكثر من رأس المال. استخدم رأس مال المخاطر فقط. الأداء السابق ليس مؤشراً على النتائج المستقبلية.",
              hypoTitle: "إفصاح الأداء الافتراضي:",
              hypoText:
                "النتائج الافتراضية لها قيود كثيرة ولا تعكس بالضرورة النتائج الفعلية. التداول الحقيقي يتضمن مخاطرة وقد تختلف النتائج بشكل كبير.",
              liveTitle: "إفصاح غرفة التداول المباشر:",
              liveText:
                "هذا العرض للأغراض التعليمية فقط. جميع الصفقات المعروضة افتراضية وقد لا يمكن تكرارها في حساب حقيقي.",
              testTitle: "إفصاح الشهادات:",
              testText:
                "الشهادات قد لا تمثل جميع المستخدمين وليست ضماناً للأداء أو النجاح مستقبلاً.",
            },
            benefits: {
              title: "المميزات الإضافية التي ستحصل عليها عند إنضمامك إلى المنتورشيب",
              subtitle:
                "",
              items: [
                {
                  title: "إمكانية تواصل مباشر مع هرمس من خلال جلسات 1v1",
                  desc: "جلسة مباشرة لمراجعة خطتك، الإجابة على أسئلتك، وتحديد نقاط التحسن بدقة.",
                },
                {
                  title: "كن من أوائل مستخدمي أدوات Talaria",
                  desc: "وصول مبكر لأحدث أدوات Talaria-Log قبل إطلاقها للعامة مع تحديثات مستمرة.",
                },
                {
                  title: "متابعة ودعم بعد انتهاء المِنتورشيب",
                  desc: "إرشادات متابعة وخطوات واضحة لما بعد البرنامج لضمان الاستمرارية وتثبيت العادات الصحيحة.",
                },
              ],
            },
            mentorSpotlight: {
              title: "هيرمس — مدربك في الرحلة",
              subtitle:
                "هيرمس سيقود رحلة المنتورشيب خطوة بخطوة، ويمنحك خارطة طريق واضحة، وتوجيه عملي، ومتابعة تساعدك على تطوير التنفيذ والانضباط.",
              points: [
                "خطة واضحة ومسار تدريجي طوال مدة البرنامج.",
                "مراجعة التنفيذ وتصحيح الأخطاء وتطوير العقلية.",
                "متابعة ودعم داخل السيرفر مع إجابات منظمة.",
              ],
            },
            startCampaign: {
              kicker: "البداية",
              title: "المنتورشيب يبدأ في 7 يوليو",
              subtitle:
                "رحلة مكثفة لتطوير مهاراتك في التداول والتنفيذ ضمن بيئة متابعة وتوجيه — مقاعد محدودة للحفاظ على جودة التجربة.",
              cta: "احجز مقعدك الآن",
              note: "كلما حجزت مبكراً، كان تجهيز حسابك وخطتك أسهل قبل البداية.",
            },
          }
        : {
            nav: { backHome: "Back Home" },
            tabs: { bootcamp: "Mentorship", soon: "Soon" },
            header: {
              a: "Trading",
              b: "Mentorship",
              subtitle:
                "Master the art of trading with our comprehensive Mentorship. Learn from the basics to advanced strategies.",
              joinNow: "Join Now",
            },
            stats: {
              modules: "Modules",
              sessions: "Sessions",
              hours: "Hours",
              tools: " free Talaria-Log tools",
              toolsValue: "2 Month",
            },
            module: {
              details: "Module details",
              lessons: "lessons",
              comingSoon: "Coming Soon",
            },
            disclosures: {
              riskTitle: "Risk Disclosure:",
              riskText:
                "Futures and forex trading contains substantial risk and is not for every investor. An investor could potentially lose all or more than the initial investment. Risk capital is money that can be lost without jeopardizing ones' financial security or life style. Only risk capital should be used for trading and only those with sufficient risk capital should consider trading. Past performance is not necessarily indicative of future results.",
              hypoTitle: "Hypothetical Performance Disclosure:",
              hypoText:
                "Hypothetical performance results have many inherent limitations, some of which are described below. No representation is being made that any account will or is likely to achieve profits or losses similar to those shown; in fact, there are frequently sharp differences between hypothetical performance results and the actual results subsequently achieved by any particular trading program. One of the limitations of hypothetical performance results is that they are generally prepared with the benefit of hindsight. In addition, hypothetical trading does not involve financial risk, and no hypothetical trading record can completely account for the impact of financial risk of actual trading. for example, the ability to withstand losses or to adhere to a particular trading program in spite of trading losses are material points which can also adversely affect actual trading results. There are numerous other factors related to the markets in general or to the implementation of any specific trading program which cannot be fully accounted for in the preparation of hypothetical performance results and all which can adversely affect trading results.",
              liveTitle: "Live Trade Room Disclosure:",
              liveText:
                "This presentation is for educational purposes only and the opinions expressed are those of the presenter only. All trades presented should be considered hypothetical and should not be expected to be replicated in a live trading account. ",
              testTitle: "Testimonial Disclosure:",
              testText:
                "Testimonials appearing on this website may not be representative of other clients or customers and is not a guarantee of future performance or success.",
            },
            benefits: {
              title: "Mentorship benefits",
              subtitle:
                "A focused experience designed to accelerate your growth — direct access, early tools, and continued support after the program.",
              items: [
                {
                  title: "Live call with Hermes",
                  desc: "A live session to review your plan, answer questions, and pinpoint your next improvements.",
                },
                {
                  title: "Be among the first Talaria tools users",
                  desc: "Early access to the latest Talaria-Log tools before public release, with ongoing updates.",
                },
                {
                  title: "Follow-up support after mentorship",
                  desc: "Post-program guidance and a clear next-step roadmap to stay consistent and keep progressing.",
                },
              ],
            },
            mentorSpotlight: {
              title: "Hermes — your mentor",
              subtitle:
                "Hermes will lead the entire mentorship journey, guiding you step-by-step with a structured roadmap, practical feedback, and ongoing support to level up your execution.",
              points: [
                "A clear roadmap and a structured weekly journey.",
                "Execution reviews, corrections, and mindset improvements.",
                "Organized support inside the server with timely answers.",
              ],
            },
            startCampaign: {
              kicker: "Starts",
              title: "Mentorship starts July 7",
              subtitle:
                "A focused, high-intensity journey designed to sharpen your trading execution — limited seats to keep quality high.",
              cta: "Secure your spot",
              note: "Joining early gives you time to prepare your setup and plan before day one.",
            },
          },
    [isArabic]
  );

  const modules = React.useMemo(
    () => (isArabic ? bootcampModulesAr : bootcampModules),
    [isArabic]
  );

  const [dropdownOpen, setDropdownOpen] = React.useState(false);
  const dropdownRef = React.useRef<HTMLDivElement | null>(null);

  React.useEffect(() => {
    if (!dropdownOpen) return;

    const onPointerDown = (e: MouseEvent | TouchEvent) => {
      const targetNode = e.target as Node | null;
      if (!dropdownRef.current || !targetNode) return;
      if (!dropdownRef.current.contains(targetNode)) {
        setDropdownOpen(false);
      }
    };

    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") setDropdownOpen(false);
    };

    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("touchstart", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("touchstart", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [dropdownOpen]);

  return (
    <main className="relative min-h-screen bg-[#030014] overflow-x-hidden">
      {/* Background */}
      <div className="fixed inset-0 -z-10 pointer-events-none bg-gradient-to-b from-black via-[#030014] to-[#0a0a1a]" />
      <div className="fixed inset-0 -z-10 pointer-events-none bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-blue-900/20 via-transparent to-transparent" />
      
      {/* Sparkles Background */}
      <div
        className="fixed inset-0 -z-10 w-full h-full pointer-events-none opacity-60 bg-[radial-gradient(circle,rgba(99,102,241,0.22)_1px,transparent_1px)] [background-size:26px_26px]"
      />

      {/* Navigation */}
      <nav className="relative z-50 px-2 sm:px-6 py-3 sm:py-4 border-b border-white/5">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div
            className="relative"
            ref={dropdownRef}
          >
              <motion.div
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.5 }}
                className="flex items-center gap-2 cursor-pointer select-none"
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  setDropdownOpen(!dropdownOpen);
                }}
              >
                <Image src="/logo-04.png" alt="Talaria" width={40} height={40} className="h-8 w-8 sm:h-10 sm:w-10" />
                <span className="text-base sm:text-2xl font-bold text-white whitespace-nowrap">Talaria-Log</span>
                <ChevronDown 
                  className={`h-5 w-5 text-white/80 transition-transform duration-200 ${dropdownOpen ? 'rotate-180' : ''}`} 
                  strokeWidth={2.5}
                />
              </motion.div>
            {dropdownOpen && (
              <motion.div 
                initial={{ opacity: 0, y: -20, scale: 0.95 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: -10, scale: 0.95 }}
                transition={{ duration: 0.25, ease: [0.4, 0, 0.2, 1] }}
                className="absolute top-full right-0 sm:left-0 sm:right-auto pt-2 z-[100]"
              >
                <div className="w-72 sm:w-80 max-w-[calc(100vw-1rem)] rounded-2xl bg-[#08080f]/98 backdrop-blur-xl border border-purple-500/20 shadow-2xl shadow-purple-900/30 p-3 sm:p-4">
                  <div className="flex flex-col gap-3">
                  {talariaBrands.map((brand, index) => {
                    const cardStyles = [
                      { color: '#eab308', ring: 'ring-yellow-500/60 shadow-yellow-500/30' },
                      { color: '#ec4899', ring: 'ring-pink-500/60 shadow-pink-500/30' },
                      { color: '#06b6d4', ring: 'ring-cyan-500/60 shadow-cyan-500/30' },
                      { color: '#3b82f6', ring: 'ring-blue-500/60 shadow-blue-500/30' },
                    ];
                    const style = cardStyles[index];
                    const suffix = brand.name.includes('-') ? brand.name.split('-').slice(1).join('-') : brand.name;
                    return (
                      <motion.div
                        key={brand.name}
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ duration: 0.3, delay: index * 0.08, ease: "easeOut" }}
                        whileHover={{ scale: 1.03 }}
                        className="group relative flex items-center justify-center p-5 rounded-xl overflow-hidden cursor-not-allowed shadow-lg bg-black pointer-events-auto select-none"
                        onClick={(e) => e.preventDefault()}
                      >
                        <div className="absolute inset-0 overflow-hidden">
                          <motion.div 
                            className="absolute w-32 h-32 rounded-full blur-2xl"
                            animate={{ 
                              x: ['-20%', '120%', '-20%'],
                              y: ['0%', '50%', '0%'],
                              scale: [1, 1.2, 1]
                            }}
                            transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
                            style={{ background: style.color, opacity: 0.4 }}
                          />
                          <motion.div 
                            className="absolute w-24 h-24 rounded-full blur-xl"
                            animate={{ 
                              x: ['100%', '-20%', '100%'],
                              y: ['60%', '10%', '60%'],
                              scale: [1.1, 0.9, 1.1]
                            }}
                            transition={{ duration: 5, repeat: Infinity, ease: "easeInOut", delay: 0.5 }}
                            style={{ background: style.color, opacity: 0.3 }}
                          />
                        </div>
                        <span className="relative z-10 text-lg font-semibold text-white text-center" aria-label={brand.name}>
                          Talaria-<span className="tg-spoiler">{suffix}</span>
                        </span>
                      </motion.div>
                    );
                  })}
                  </div>
                </div>
              </motion.div>
            )}
          </div>
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.5, delay: 0.2 }}
            className="flex items-center gap-2 sm:gap-4 flex-wrap justify-end"
          >
            <Link href="/">
              <Button variant="ghost" className="text-white hover:text-blue-400 px-3 sm:px-4">
                <ArrowLeft className={`w-4 h-4 ${isArabic ? "ml-2" : "mr-2"}`} />
                {t.nav.backHome}
              </Button>
            </Link>
          </motion.div>
        </div>
      </nav>

      {/* Tabs Section */}
      <div className="relative z-40 px-2 sm:px-6 py-3 sm:py-4 border-b border-white/5">
        <div className="max-w-7xl mx-auto flex justify-center">
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.3 }}
            className="flex items-center justify-center gap-2 sm:gap-7 flex-wrap"
          >
            <Link href="/bootcamp">
              <Button className="rounded-full text-sm sm:text-base px-4 py-3 sm:px-8 sm:py-6 text-white bg-gradient-to-r from-black via-blue-900 to-blue-600 hover:from-black hover:via-blue-800 hover:to-blue-500 shadow-[0_0_0_1px_rgba(59,130,246,0.25),0_18px_45px_rgba(37,99,235,0.25)] hover:shadow-[0_0_0_1px_rgba(59,130,246,0.4),0_22px_55px_rgba(37,99,235,0.32)] transition-all">
                {t.tabs.bootcamp}
              </Button>
            </Link>
            <div className="relative group">
              <Button className="rounded-full text-sm sm:text-base px-4 py-3 sm:px-8 sm:py-6 text-white/50 bg-gradient-to-r from-black via-blue-900/50 to-blue-600/50 shadow-[0_0_0_1px_rgba(59,130,246,0.15),0_18px_45px_rgba(37,99,235,0.15)] cursor-not-allowed opacity-60">
                <span className="tg-mask" aria-hidden="true" />
              </Button>
              <span className="absolute -top-1 -right-1 bg-yellow-500 text-black text-[8px] sm:text-[10px] px-1.5 py-0.5 rounded-full font-semibold">{t.tabs.soon}</span>
            </div>
            <Link href="/ninjatrader">
              <Button variant="ghost" className="px-2 sm:px-4 py-1 text-sm rounded-full h-6 sm:h-8 flex items-center bg-transparent hover:bg-white/10">
                <Image
                  src={NinjaTraderWordmark}
                  alt="NinjaTrader"
                  width={112}
                  height={16}
                  className="h-3 sm:h-4 w-auto object-contain mix-blend-screen"
                />
              </Button>
            </Link>
          </motion.div>
        </div>
      </div>

      {/* Page Content */}
      <div className="relative z-10 px-4 sm:px-6 py-10 sm:py-12">
        <div className="max-w-7xl mx-auto">
          {joinMenuOpen && (
            <div
              className="fixed inset-0 z-[200] flex items-center justify-center bg-black/70 px-4"
              onClick={() => setJoinMenuOpen(false)}
            >
              <div
                className="w-full max-w-md rounded-2xl border border-white/10 bg-[#0b0b16] p-5 shadow-2xl"
                onClick={(e) => e.stopPropagation()}
              >
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <div className="text-lg font-semibold text-white">
                      {isArabic ? "تسجيل الدخول أو إنشاء حساب" : "Sign in or create an account"}
                    </div>
                    <div className="mt-1 text-sm text-white/70">
                      {isArabic ? "للإكمال، اختر تسجيل الدخول أو إنشاء حساب." : "To continue, choose Sign in or Sign up."}
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => setJoinMenuOpen(false)}
                    className="rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-sm text-white/80 hover:bg-white/10"
                  >
                    {isArabic ? "إغلاق" : "Close"}
                  </button>
                </div>

                <div className="mt-5 grid grid-cols-1 gap-3">
                  <Link href="/login/?mode=signin&next=/register/">
                    <Button className="w-full rounded-xl bg-white text-black hover:bg-white/90">
                      {isArabic ? "تسجيل الدخول" : "Sign in"}
                    </Button>
                  </Link>
                  <Link href="/login/?mode=signup&next=/register/">
                    <Button className="w-full rounded-xl text-white bg-gradient-to-r from-blue-600 via-indigo-600 to-cyan-500 hover:from-blue-500 hover:via-indigo-500 hover:to-cyan-400">
                      {isArabic ? "إنشاء حساب" : "Sign up"}
                    </Button>
                  </Link>
                </div>
              </div>
            </div>
          )}

          {/* Header */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: false, amount: 0.35 }}
            transition={{ duration: 0.6 }}
            className="text-center mb-10"
          >
            <div className="flex justify-center mb-6">
              <Image
                src={HermesLogo}
                alt="Hermes Logo"
                width={160}
                height={196}
                className="w-24 sm:w-28 md:w-32 h-auto"
                priority
              />
            </div>
            <h1 className="text-4xl sm:text-5xl md:text-6xl font-bold text-white mb-4">
              {t.header.a}{" "}
              <span className="bg-clip-text text-transparent bg-gradient-to-r from-blue-500 via-blue-400 to-cyan-400">
                {t.header.b}
              </span>
            </h1>
            <p className="text-neutral-300 text-lg sm:text-xl max-w-2xl mx-auto">
              {t.header.subtitle}
            </p>
            <motion.div
              animate={{ y: [0, -6, 0] }}
              transition={{ duration: 2.6, repeat: Infinity, ease: "easeInOut" }}
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.98 }}
              className="mt-8 flex flex-col items-center"
            >
              <Button
                type="button"
                onClick={handleJoinNow}
                disabled={joinMenuLoading}
                className="rounded-full text-base px-7 py-5 sm:px-8 sm:py-6 text-white bg-gradient-to-r from-black via-blue-900 to-blue-600 hover:from-black hover:via-blue-800 hover:to-blue-500 shadow-[0_0_0_1px_rgba(59,130,246,0.25),0_18px_45px_rgba(37,99,235,0.25)] hover:shadow-[0_0_0_1px_rgba(59,130,246,0.4),0_22px_55px_rgba(37,99,235,0.32)] transition-all"
              >
                {joinMenuLoading ? (isArabic ? "...جاري التحقق" : "Checking...") : t.header.joinNow}
              </Button>
              <div className="mt-2 text-center text-sm text-white/70">700$</div>
            </motion.div>
          </motion.div>

          <div className="rounded-[32px] border border-white/10 bg-[#0f0f23]/45 shadow-[0_30px_120px_rgba(0,0,0,0.55)] overflow-hidden">
            <div className="p-6 sm:p-10">

          {/* Stats */}
          {/* Stats */}
<svg width="0" height="0" className="absolute">
  <defs>
    <linearGradient id="statIconGradient" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stopColor="#232cf4" />
      <stop offset="100%" stopColor="#2d78fc" />
    </linearGradient>
  </defs>
</svg>

<div className="grid grid-cols-2 md:grid-cols-4 gap-4 sm:gap-6"></div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 sm:gap-6">
            {[
              { icon: BookOpen, label: t.stats.modules, value: "4" },
              { icon: PlayCircle, label: t.stats.sessions, value: "20" },
              { icon: Target, label: t.stats.hours, value: "+60" },
              { icon: Trophy, label: t.stats.tools, value: t.stats.toolsValue, highlight: true },
            ].map((stat, index) => (
              <motion.div
                key={stat.label}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: false, amount: 0.3 }}
                transition={{ duration: 0.5, delay: index * 0.1 }}
                whileHover={
                  (stat as any).highlight
                    ? { y: -12, scale: 1.05 }
                    : undefined
                }
                whileTap={(stat as any).highlight ? { scale: 0.99 } : undefined}
                className={
                  "group relative isolate h-full min-h-[120px] overflow-hidden rounded-2xl p-[1.25px] text-center z-0 " +
                  ((stat as any).highlight ? "cursor-pointer hover:z-10" : "")
                }
              >
                <GlowEffect
                  className={
                    ((stat as any).highlight ? "opacity-90" : "opacity-55") +
                    " -z-10 rounded-2xl"
                  }
                  colors={["#0894FF", "#C959DD", "#FF2E54", "#FF9004"]}
                  mode="static"
                  blur="none"
                  duration={6}
                  scale={1}
                />

                <div className="relative z-10 h-full rounded-[15px] bg-black px-4 py-5 sm:px-6 sm:py-6 flex flex-col items-center justify-center">
                  <div
                    aria-hidden="true"
                    className="absolute inset-0 rounded-[15px] ring-1 ring-white/10 group-hover:ring-white/20 transition-colors"
                  />
                  <div
                    aria-hidden="true"
                    className="absolute inset-0 rounded-[15px] bg-gradient-to-b from-white/7 via-transparent to-transparent"
                  />
                  {(stat as any).highlight ? (
                    <div
                      aria-hidden="true"
                      className={
                        "absolute top-0 " +
                        (isArabic ? "left-0" : "right-0") +
                        " w-28 h-28 sm:w-40 sm:h-40 overflow-hidden pointer-events-none"
                      }
                    >
                      <div
                        className={
                          "absolute top-2 sm:top-3 " +
                          (isArabic ? "-left-12 sm:-left-16 -rotate-45" : "-right-12 sm:-right-16 rotate-45")
                        }
                      >
                        <div className="relative flex items-center justify-center rounded-sm bg-gradient-to-r from-emerald-400 via-emerald-500 to-emerald-600 text-black w-40 sm:w-56 px-0 py-2 sm:py-3 text-[10px] sm:text-[13px] font-extrabold">
                          <div
                            dir={isArabic ? "rtl" : "ltr"}
                            className="relative z-10 leading-none text-center"
                          >
                            <div className="flex flex-row items-center justify-center gap-1.5 w-full font-zain">
                              <span className="text-[12px] sm:text-[14px] font-semibold text-gray-600 line-through decoration-gray-600" dir="ltr">
                                $100
                              </span>
                              <span className="text-[12px] sm:text-[14px] font-semibold text-black" dir="ltr">
                                $0
                              </span>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  ) : null}
                  <div className="relative">
                    <div className="mx-auto mb-2 sm:mb-3 inline-flex h-12 w-12 items-center justify-center">
                      {(stat as any).highlight ? (
                        <Image
                          src="/logo-04.png"
                          alt="Talaria"
                          width={44}
                          height={44}
                          className="h-12 w-12 sm:h-20 sm:w-20 object-contain"
                        />
                      ) : (
                        <stat.icon
                          className="h-15 w-17 sm:h-8 sm:w-8"
                          stroke="url(#statIconGradient)"
                          strokeWidth={2.4}
                        />
                      )}
                    </div>
                    <div className="text-xl sm:text-3xl md:text-4xl leading-tight font-bold text-white tracking-tight">{stat.value}</div>
                    <div className="text-neutral-400 text-[10px] sm:text-sm leading-tight">{stat.label}</div>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>

          <div className="my-10 h-px bg-white/10" />

          {/* Benefits */}
          <div>
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: false, amount: 0.35 }}
              transition={{ duration: 0.6 }}
              className="text-center mb-8"
            >
              <div className="text-white text-2xl sm:text-3xl font-bold mb-2">
                {t.benefits.title}
              </div>
              <div className="text-neutral-400 text-sm sm:text-base max-w-3xl mx-auto">
                {t.benefits.subtitle}
              </div>
            </motion.div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 sm:gap-6">
              {[
                { item: t.benefits.items[0] },
                { item: t.benefits.items[1] },
                { item: t.benefits.items[2] },
              ].map((b, index) => (
                <motion.div
                  key={b.item.title}
                  initial={{ opacity: 0, y: 18 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: false, amount: 0.25 }}
                  transition={{ duration: 0.55, delay: index * 0.08 }}
                  whileHover={{ y: -8, scale: 1.02 }}
                  whileTap={{ scale: 0.99 }}
                  className="group relative isolate h-full min-h-[220px] overflow-hidden rounded-2xl p-[1.25px] z-0"
                >
                  <GlowEffect
                    className="opacity-90 -z-10 rounded-2xl"
                    colors={["#0894FF", "#C959DD", "#FF2E54", "#FF9004"]}
                    mode="static"
                    blur="none"
                    duration={6}
                    scale={1}
                  />

                  <div className="relative z-10 h-full rounded-[15px] bg-black px-5 py-5 sm:px-6 sm:py-6 flex flex-col">
                    <div
                      aria-hidden="true"
                      className="absolute inset-0 rounded-[15px] ring-1 ring-white/10 group-hover:ring-white/20 transition-colors pointer-events-none"
                    />
                    <div
                      aria-hidden="true"
                      className="absolute inset-0 rounded-[15px] bg-gradient-to-b from-white/7 via-transparent to-transparent pointer-events-none"
                    />

                    <div className="relative h-full flex flex-col">
                      <div
                        className={
                          "text-white font-semibold text-lg mb-2 min-h-[52px] " +
                          (isArabic ? "text-right" : "text-left")
                        }
                      >
                        {b.item.title}
                      </div>
                      <div
                        className={
                          "text-neutral-400 text-base leading-relaxed flex-1 " +
                          (isArabic ? "text-right" : "text-left")
                        }
                      >
                        {b.item.desc}
                      </div>
                    </div>
                  </div>
                </motion.div>
              ))}
            </div>
          </div>

          <div className="my-10 h-px bg-white/10" />

          {/* Modules */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {modules.map((module, index) => (
              <motion.div
                key={module.title}
                initial={{ opacity: 0, x: -20 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: false, amount: 0.25 }}
                transition={{ duration: 0.5, delay: index * 0.1 }}
                whileHover={module.status === "available" ? { y: -6, scale: 1.01 } : undefined}
                whileTap={module.status === "available" ? { scale: 0.99 } : undefined}
                className={
                  "group relative isolate h-full min-h-[270px] overflow-hidden rounded-2xl p-[1.25px] z-0 " +
                  (module.status === "available"
                    ? "cursor-pointer hover:z-10"
                    : "opacity-70 cursor-not-allowed")
                }
              >
                <GlowEffect
                  className={
                    (module.status === "available" ? "opacity-90" : "opacity-40") +
                    " -z-10 rounded-2xl"
                  }
                  colors={["#0894FF", "#C959DD", "#FF2E54", "#FF9004"]}
                  mode="static"
                  blur="none"
                  duration={6}
                  scale={1}
                />

                <div className="relative z-10 h-full rounded-[15px] bg-black px-4 py-5 sm:px-6 sm:py-6 flex flex-col">
                  <div
                    aria-hidden="true"
                    className="absolute inset-0 rounded-[15px] ring-1 ring-white/10 group-hover:ring-white/20 transition-colors"
                  />
                  <div
                    aria-hidden="true"
                    className="absolute inset-0 rounded-[15px] bg-gradient-to-b from-white/7 via-transparent to-transparent"
                  />

                  <div className="relative">
                    <div className="flex items-center gap-3 mb-2">
                      <h3
                        className={
                          "text-lg sm:text-xl font-semibold " +
                          (module.status === "available" ? "text-white" : "text-white/60")
                        }
                      >
                        {module.title}
                      </h3>
                      {module.status === "coming_soon" && (
                        <span className="bg-yellow-500/20 text-yellow-500 text-xs px-2 py-1 rounded-full font-medium">
                          {t.module.comingSoon}
                        </span>
                      )}
                      {module.status === "available" && (
                        <CheckCircle className="w-5 h-5 text-green-500" />
                      )}
                    </div>
                    <p
                      className={
                        (module.status === "available"
                          ? "text-neutral-300"
                          : "text-neutral-600") + " mb-4"
                      }
                    >
                      {module.description}
                    </p>

                    <div className="rounded-xl border border-white/10 bg-white/5 p-3 sm:p-4 mb-4">
                      <div className="text-white/90 text-sm font-semibold mb-2">
                        {t.module.details}
                      </div>
                      <ul className="space-y-2">
                        {module.details.map((item: string) => (
                          <li key={item} className="text-neutral-300/80 text-sm flex gap-2">
                            <span className="text-white/60">•</span>
                            <span>{item}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>

                  <div className="relative mt-auto flex items-center gap-4 text-sm">
                    <span
                      className={
                        module.status === "available"
                          ? "text-white/80"
                          : "text-neutral-600"
                      }
                    >
                      {module.lessons} {t.module.lessons}
                    </span>
                    <span
                      className={
                        module.status === "available"
                          ? "text-white/60"
                          : "text-neutral-600"
                      }
                    >
                      {module.duration}
                    </span>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>

          <motion.div
            animate={{ y: [0, -6, 0] }}
            transition={{ duration: 2.6, repeat: Infinity, ease: "easeInOut" }}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.98 }}
            className="mt-12 flex justify-center"
          >
            <div className="text-center">
              <Button
                type="button"
                onClick={handleJoinNow}
                disabled={joinMenuLoading}
                className="rounded-full text-base px-8 py-5 sm:px-10 sm:py-6 text-white bg-gradient-to-r from-black via-blue-900 to-blue-600 hover:from-black hover:via-blue-800 hover:to-blue-500 shadow-[0_0_0_1px_rgba(59,130,246,0.25),0_18px_45px_rgba(37,99,235,0.25)] hover:shadow-[0_0_0_1px_rgba(59,130,246,0.4),0_22px_55px_rgba(37,99,235,0.32)] transition-all"
              >
                {joinMenuLoading ? (isArabic ? "...جاري التحقق" : "Checking...") : t.header.joinNow}
              </Button>
              <div className="mt-2 text-sm text-white/70">700$</div>
            </div>
          </motion.div>

            </div>
          </div>
        </div>
      </div>

      <SiteDisclosuresFooter />
    </main>
  );
}
