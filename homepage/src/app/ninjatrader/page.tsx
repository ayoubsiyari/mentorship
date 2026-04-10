"use client";
import React from "react";
import { motion } from "framer-motion";
import Link from "next/link";
import Image from "next/image";
import { ChevronDown, ArrowLeft, ExternalLink } from "lucide-react";
import { SparklesCore } from "@/components/ui/sparkles";
import { Button } from "@/components/ui/button";
import SiteDisclosuresFooter from "@/components/SiteDisclosuresFooter";

import NinjaTraderWordmark from "../../../ninjatrader/Landing-Page-Text-Images/NinjaTrader/NinjaTrader_Wordmark_color_RGB.png";
import NinjaTraderMonitor from "../../../ninjatrader/Landing-Page-Text-Images/NinjaTrader/NinjaTrader_Monitor_Image.png";
import KinetickBadge from "../../../ninjatrader/Landing-Page-Text-Images/Kinetick/Kinetick_Badge.png";
import KinetickLogo from "../../../ninjatrader/Landing-Page-Text-Images/Kinetick/Kinetick_Logo.png";

const talariaBrands = [
  { name: "Talaria-Prop", href: "#" },
  { name: "Talaria-Flow", href: "#" },
  { name: "Talaria-Copy", href: "#" },
];

export default function NinjaTraderPage() {
  const isArabic = false;
  const t = React.useMemo(
    () =>
      isArabic
        ? {
            nav: { backHome: "العودة للرئيسية" },
            hero: {
              title: "منصة التداول الموصى بها",
              p1:
                "NinjaTrader® هي منصة التداول رقم 1 الموصى بها لدينا والمفضلة لدى المتداولين حول العالم، بما في ذلك عملاؤنا.",
              p2: "قم بتحميل NinjaTrader واحصل فوراً على وصول مجاني إلى:",
              bullets: [
                "بيانات العقود الآجلة في الوقت الحقيقي",
                "رسوم بيانية متقدمة",
                "محاكي التداول",
                "تطوير الاستراتيجيات والاختبار الخلفي",
              ],
              p3:
                "تُصنَّف منصة NinjaTrader الحائزة على جوائز باستمرار كقائد في الصناعة من قبل مجتمع المتداولين. مع آلاف التطبيقات والإضافات للتخصيص غير المحدود، يستخدمها أكثر من 500,000 متداول لتحليل الأسواق والرسوم الاحترافية وتنفيذ الأوامر بسرعة.",
              p4:
                "للمتداولين الجدد، ابدأ التحضير للأسواق الحية باستخدام محاكي تداول مجاني مزود ببيانات سوق في الوقت الحقيقي.",
              ctas: {
                platform: "منصة التداول",
                download: "تحميل NinjaTrader",
                simulator: "محاكي التداول",
                startFree: "ابدأ مجاناً!",
              },
            },
            data: {
              title: "مصدر بيانات السوق الموصى به",
              p1:
                "Kinetick® يوفر بيانات سوق موثوقة وسريعة وبتكلفة فعّالة لمساعدة المتداولين النشطين. استفد من عروض الأسعار غير المفلترة وفي الوقت الحقيقي للأسهم والعقود الآجلة والفوركس.",
              p2:
                "ابدأ ببيانات تاريخية مجانية لنهاية اليوم (EOD) مباشرة عبر منصة NinjaTrader وتعرّف على كيفية تقليل رسوم البورصة لبيانات السوق في الوقت الحقيقي عبر Kinetick.",
              ctas: {
                marketData: "بيانات السوق",
                historical: "بيانات تاريخية للسوق",
                freeEod: "ابدأ مع بيانات EOD مجاناً",
              },
            },
            disclaimers: {
              title: "إخلاءات المسؤولية",
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
          }
        : {
            nav: { backHome: "Back Home" },
            hero: {
              title: "Our Recommended Trading Platform",
              p1:
                "NinjaTrader® is our #1 recommended trading software platform preferred by traders worldwide including our clients.",
              p2: "Download NinjaTrader & receive immediate FREE access to:",
              bullets: [
                "Real-time futures data",
                "Advanced charting",
                "Trade simulator",
                "Strategy development and backtesting",
              ],
              p3:
                "NinjaTrader’s award-winning trading platform is consistently voted an industry leader by the trading community. Featuring 1000s of Apps & Add-Ons for unlimited customization, NinjaTrader is used by over 500,000 traders for advanced market analysis, professional charting and fast order execution.",
              p4:
                "For new traders, start preparing for the live markets with a free trading simulator featuring real-time market data.",
              ctas: {
                platform: "Trading platform",
                download: "Download NinjaTrader",
                simulator: "Trading simulator",
                startFree: "Get Started for FREE!",
              },
            },
            data: {
              title: "Our Recommended Market Data Feed",
              p1:
                "Kinetick® delivers reliable, fast and cost-effective market data to help level the playing field for active traders. Take advantage of unfiltered, real time quotes for stocks, futures and forex that exceed the expectations of the world’s most demanding traders, like us!",
              p2:
                "Get started with FREE end-of-day historical market data directly through the NinjaTrader platform and learn how you can significantly reduce CME Group Globex exchange fees on real-time market data with Kinetick.",
              ctas: {
                marketData: "Market data",
                historical: "Historical market data",
                freeEod: "Get Started with Free EOD Data",
              },
            },
            disclaimers: {
              title: "Disclaimers",
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
          },
    [isArabic]
  );

  const [dropdownOpen, setDropdownOpen] = React.useState(false);
  const closeTimeoutRef = React.useRef<NodeJS.Timeout | null>(null);

  const handleMouseEnter = () => {
    if (closeTimeoutRef.current) {
      clearTimeout(closeTimeoutRef.current);
      closeTimeoutRef.current = null;
    }
    setDropdownOpen(true);
  };

  const handleMouseLeave = () => {
    closeTimeoutRef.current = setTimeout(() => {
      setDropdownOpen(false);
    }, 300);
  };

  // Close dropdown when clicking outside
  React.useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      if (dropdownOpen && !target.closest('[data-dropdown-container]')) {
        setDropdownOpen(false);
      }
    };
    document.addEventListener('click', handleClickOutside);
    return () => document.removeEventListener('click', handleClickOutside);
  }, [dropdownOpen]);

  return (
    <main
      dir="ltr"
      lang="en"
      className="relative min-h-screen bg-[#030014] overflow-x-hidden text-left"
    >
      <div className="pointer-events-none fixed inset-0 -z-10 bg-gradient-to-b from-black via-[#030014] to-[#0a0a1a]" />
      <div className="pointer-events-none fixed inset-0 -z-10 bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-blue-900/20 via-transparent to-transparent" />

      <div className="pointer-events-none fixed inset-0 -z-10 w-full h-full">
        <SparklesCore
          id="tsparticles-ninjatrader"
          background="transparent"
          minSize={0.4}
          maxSize={1.2}
          particleDensity={70}
          className="w-full h-full"
          particleColor="#6366f1"
          speed={0.45}
        />
      </div>

      <nav className="relative z-50 px-2 sm:px-6 py-3 sm:py-4 border-b border-white/5">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div
            className="relative"
            data-dropdown-container
            onMouseEnter={handleMouseEnter}
            onMouseLeave={handleMouseLeave}
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
                <img
                  src="/logo-04.png"
                  alt="Talaria"
                  className="h-8 w-8 sm:h-10 sm:w-10"
                />
                <span className="text-base sm:text-2xl font-bold text-white whitespace-nowrap">Talaria-Log</span>
                <ChevronDown
                  className={`h-5 w-5 text-white/80 transition-transform duration-200 ${
                    dropdownOpen ? "rotate-180" : ""
                  }`}
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
                        { color: "#eab308" },
                        { color: "#ec4899" },
                        { color: "#06b6d4" },
                        { color: "#3b82f6" },
                      ];
                      const style = cardStyles[index];
                      const suffix = brand.name.includes("-")
                        ? brand.name.split("-").slice(1).join("-")
                        : brand.name;
                      return (
                        <motion.div
                          key={brand.name}
                          initial={{ opacity: 0, x: -20 }}
                          animate={{ opacity: 1, x: 0 }}
                          transition={{
                            duration: 0.3,
                            delay: index * 0.08,
                            ease: "easeOut",
                          }}
                          whileHover={{ scale: 1.03 }}
                          className="group relative flex items-center justify-center p-5 rounded-xl overflow-hidden cursor-not-allowed shadow-lg bg-black pointer-events-auto select-none"
                          onClick={(e) => e.preventDefault()}
                        >
                          <div className="absolute inset-0 overflow-hidden">
                            <motion.div
                              className="absolute w-32 h-32 rounded-full blur-2xl"
                              animate={{
                                x: ["-20%", "120%", "-20%"],
                                y: ["0%", "50%", "0%"],
                                scale: [1, 1.2, 1],
                              }}
                              transition={{
                                duration: 4,
                                repeat: Infinity,
                                ease: "easeInOut",
                              }}
                              style={{ background: style.color, opacity: 0.4 }}
                            />
                          </div>
                          <span
                            className="relative z-10 text-lg font-semibold text-white text-center"
                            aria-label={brand.name}
                          >
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

      <section className="relative z-10 px-4 sm:px-6 py-12 sm:py-16">
        <div className="max-w-7xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="grid grid-cols-1 md:grid-cols-2 gap-8 sm:gap-10 items-center"
          >
            <div>
              <Image src={NinjaTraderWordmark} alt="NinjaTrader" className="h-10 md:h-12 w-auto mb-6" />
              <h1 className="text-4xl md:text-5xl font-bold text-white mb-5">{t.hero.title}</h1>
              <p className="text-white/80 text-lg leading-relaxed max-w-2xl">{t.hero.p1}</p>
              <p className="text-neutral-300 leading-relaxed mb-4">{t.hero.p2}</p>
              <ul className={`list-disc ${isArabic ? "pr-5" : "pl-5"} text-neutral-300 space-y-1 mb-4`}>
                {t.hero.bullets.map((b) => (
                  <li key={b}>{b}</li>
                ))}
              </ul>
              <p className="text-neutral-300 leading-relaxed mb-4">
                {t.hero.p3}
              </p>
              <p className="text-neutral-300 leading-relaxed mb-6">
                {t.hero.p4}
              </p>

              <div className="flex flex-col sm:flex-row flex-wrap gap-3">
                <a href="https://ninjatraderdomesticvendor.sjv.io/xJnDGk" target="_blank" rel="noreferrer" className="inline-flex">
                  <Button className="bg-purple-600 hover:bg-purple-700 text-white px-6">
                    {t.hero.ctas.platform}
                    <ExternalLink className={`w-4 h-4 ${isArabic ? "mr-2" : "ml-2"}`} />
                  </Button>
                </a>
                <a href="https://ninjatraderdomesticvendor.sjv.io/xJnDGk" target="_blank" rel="noreferrer" className="inline-flex">
                  <Button className="bg-blue-600 hover:bg-blue-700 text-white px-6">
                    {t.hero.ctas.download}
                    <ExternalLink className={`w-4 h-4 ${isArabic ? "mr-2" : "ml-2"}`} />
                  </Button>
                </a>
                <a href="https://ninjatraderdomesticvendor.sjv.io/xJnDGk" target="_blank" rel="noreferrer" className="inline-flex">
                  <Button variant="ghost" className="text-white hover:text-blue-400 px-6">
                    {t.hero.ctas.simulator}
                    <ExternalLink className={`w-4 h-4 ${isArabic ? "mr-2" : "ml-2"}`} />
                  </Button>
                </a>
                <a href="https://ninjatraderdomesticvendor.sjv.io/xJnDGk" target="_blank" rel="noreferrer" className="inline-flex">
                  <Button variant="ghost" className="text-white hover:text-blue-400 px-6">
                    {t.hero.ctas.startFree}
                    <ExternalLink className={`w-4 h-4 ${isArabic ? "mr-2" : "ml-2"}`} />
                  </Button>
                </a>
              </div>
            </div>

            <div className="relative">
              <div className="pointer-events-none absolute -inset-6 rounded-[28px] bg-gradient-to-r from-purple-500/20 via-cyan-400/10 to-blue-500/20 blur-2xl" />
              <div className="relative rounded-2xl p-[1px] bg-gradient-to-r from-purple-500/60 via-cyan-400/40 to-blue-500/60 shadow-[0_0_70px_rgba(59,130,246,0.14)]">
                <div className="relative overflow-hidden rounded-2xl bg-[#070b1b]/90 backdrop-blur-xl border border-white/10">
                  <div className="pointer-events-none absolute inset-x-0 top-0 h-28 bg-gradient-to-b from-white/10 via-white/0 to-transparent" />
                  <Image src={NinjaTraderMonitor} alt="NinjaTrader platform" className="w-full h-auto" />
                </div>
              </div>
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.1 }}
            className="mt-14 grid grid-cols-1 md:grid-cols-2 gap-10 items-center"
          >
            <div className="relative order-2 md:order-1">
              <div className="pointer-events-none absolute -inset-6 rounded-[28px] bg-gradient-to-r from-blue-500/20 via-cyan-400/10 to-purple-500/20 blur-2xl" />
              <div className="relative rounded-2xl p-[1px] bg-gradient-to-r from-blue-500/60 via-cyan-400/40 to-purple-500/60 shadow-[0_0_70px_rgba(59,130,246,0.14)]">
                <div className="relative overflow-hidden rounded-2xl bg-[#070b1b]/90 backdrop-blur-xl border border-white/10 p-12 md:p-14 flex flex-col items-center justify-center text-center">
                  <Image src={KinetickBadge} alt="FREE end-of-day data" className="h-36 md:h-44 w-auto drop-shadow-[0_0_24px_rgba(255,255,255,0.18)]" />
                  <Image src={KinetickLogo} alt="Kinetick" className="h-16 md:h-18 w-auto mt-8 drop-shadow-[0_0_18px_rgba(255,255,255,0.12)]" />
                </div>
              </div>
            </div>

            <div className="order-1 md:order-2">
              <h2 className="text-3xl md:text-4xl font-bold text-white mb-4">
                {t.data.title}
              </h2>
              <p className="text-neutral-300 leading-relaxed mb-4">
                {t.data.p1}
              </p>
              <p className="text-neutral-300 leading-relaxed mb-6">
                {t.data.p2}
              </p>

              <div className="flex flex-col sm:flex-row flex-wrap gap-3">
                <a href="http://kinetick.com/NinjaTrader" target="_blank" rel="noreferrer" className="inline-flex">
                  <Button className="bg-blue-600 hover:bg-blue-700 text-white px-6">
                    {t.data.ctas.marketData}
                    <ExternalLink className={`w-4 h-4 ${isArabic ? "mr-2" : "ml-2"}`} />
                  </Button>
                </a>
                <a href="http://kinetick.com/" target="_blank" rel="noreferrer" className="inline-flex">
                  <Button variant="ghost" className="text-white hover:text-blue-400 px-6">
                    {t.data.ctas.historical}
                    <ExternalLink className={`w-4 h-4 ${isArabic ? "mr-2" : "ml-2"}`} />
                  </Button>
                </a>
                <a href="http://kinetick.com/NinjaTrader" target="_blank" rel="noreferrer" className="inline-flex">
                  <Button className="bg-purple-600 hover:bg-purple-700 text-white px-6">
                    {t.data.ctas.freeEod}
                    <ExternalLink className={`w-4 h-4 ${isArabic ? "mr-2" : "ml-2"}`} />
                  </Button>
                </a>
              </div>
            </div>
          </motion.div>

        </div>
      </section>

      <SiteDisclosuresFooter forceLtr />
    </main>
  );
}
