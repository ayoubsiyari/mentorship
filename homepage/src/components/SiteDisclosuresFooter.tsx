"use client";

import React from "react";
import Image from "next/image";
import Link from "next/link";
import { useLanguage } from "@/app/LanguageProvider";
import { BilingualDisclosures } from "@/components/BilingualDisclosures";
import NewsletterSubscribe from "@/components/NewsletterSubscribe";

type Disclosures = {
  riskTitle: string;
  riskText: string;
  hypoTitle: string;
  hypoText: string;
  liveTitle: string;
  liveText: string;
  testTitle: string;
  testText: string;
};

type FooterCopy = {
  brandLine: string;
  legal: string;
  privacy: string;
  terms: string;
  refunds: string;
  disclaimer: string;
  ninjaTraderDisclaimer: string;
  contact: string;
  emailSupport: string;
  rights: string;
  riskLine: string;
};

export default function SiteDisclosuresFooter({
  en,
  ar,
  footer,
  forceLtr,
}: {
  en?: Disclosures;
  ar?: Disclosures;
  footer?: FooterCopy;
  /** Force left-to-right layout and English chrome (e.g. English-only partner pages). */
  forceLtr?: boolean;
}) {
  const { isArabic } = useLanguage();
  const layoutRtl = forceLtr ? false : isArabic;

  const defaultFooter = React.useMemo(
    () =>
      layoutRtl
        ? {
            footer: {
              brandLine: "أدوات تداول احترافية للمتداولين الجادّين.",
              legal: "",
              privacy: "سياسة الخصوصية",
              terms: "شروط الخدمة",
              refunds: "سياسة الاسترجاع",
              disclaimer: "إخلاء مسؤولية التداول",
              ninjaTraderDisclaimer: "Disclaimer",
              contact: "تواصل",
              emailSupport: "دعم عبر البريد الإلكتروني",
              rights: "© 2026 Talaria Log جميع الحقوق محفوظة.",
              riskLine: "",
            },
          }
        : {
            footer: {
              brandLine: "Professional trading tools for serious traders.",
              legal: "Legal",
              privacy: "Privacy Policy",
              terms: "Terms of Service",
              refunds: "Refund Policy",
              disclaimer: "Trading Disclaimer",
              ninjaTraderDisclaimer: "NinjaTrader Disclaimer",
              contact: "Contact",
              emailSupport: "Email Support",
              rights: "© 2026 Talaria Log . All rights reserved.",
              riskLine: "",
            },
          },
    [layoutRtl]
  );

  const t = React.useMemo(
    () => ({ footer: footer ? footer : defaultFooter.footer }),
    [footer, defaultFooter.footer]
  );

  const defaultDisclosuresEn: Disclosures = {
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
  };

  const defaultDisclosuresAr: Disclosures = {
    riskTitle: "إفصاح المخاطر:",
    riskText:
      "تداول العقود الآجلة والفوركس ينطوي على مخاطر كبيرة وليس مناسباً لكل مستثمر. قد يخسر المستثمر كامل أو أكثر من الاستثمار الأولي. رأس المال المعرض للمخاطر هو المال الذي يمكن خسارته دون التأثير على الأمن المالي أو نمط الحياة. ينبغي استخدام رأس مال المخاطر فقط للتداول، ولا ينبغي إلا لمن يملكون رأس مال كافٍ للتداول أن يفكروا في ذلك. الأداء السابق ليس بالضرورة مؤشراً على النتائج المستقبلية.",
    hypoTitle: "إفصاح الأداء الافتراضي:",
    hypoText:
      "لنتائج الأداء الافتراضي العديد من القيود الجوهرية، وبعضها موضح أدناه. لا يتم تقديم أي تمثيل بأن أي حساب سيحقق أو من المحتمل أن يحقق أرباحاً أو خسائر مشابهة لما هو معروض؛ في الواقع توجد غالباً فروقات كبيرة بين النتائج الافتراضية والنتائج الفعلية التي تتحقق لاحقاً لأي برنامج تداول محدد. أحد قيود النتائج الافتراضية أنها تُعد عادةً مع الاستفادة من معرفة ما حدث في الماضي. بالإضافة إلى ذلك، لا ينطوي التداول الافتراضي على مخاطرة مالية، ولا يمكن لأي سجل تداول افتراضي أن يراعي بالكامل تأثير المخاطرة المالية في التداول الفعلي. على سبيل المثال، القدرة على تحمل الخسائر أو الالتزام ببرنامج تداول معين رغم الخسائر هي نقاط مهمة قد تؤثر سلباً على النتائج الفعلية. توجد عوامل عديدة أخرى مرتبطة بالأسواق عموماً أو بتطبيق أي برنامج تداول محدد لا يمكن أخذها بالكامل في الاعتبار عند إعداد النتائج الافتراضية، وكلها قد تؤثر سلباً على نتائج التداول.",
    liveTitle: "إفصاح غرفة التداول المباشر:",
    liveText:
      "هذا العرض للأغراض التعليمية فقط والآراء المعبر عنها هي آراء المقدم فقط. جميع الصفقات المعروضة يجب اعتبارها افتراضية ولا ينبغي توقع تكرارها في حساب تداول حقيقي.",
    testTitle: "إفصاح الشهادات:",
    testText:
      "الشهادات الظاهرة على هذا الموقع قد لا تكون ممثلة لعملاء أو مستخدمين آخرين ولا تعد ضماناً للأداء أو النجاح مستقبلاً.",
  };

  const disclosuresEn = en ? en : defaultDisclosuresEn;
  const disclosuresAr = ar ? ar : defaultDisclosuresAr;

  return (
    <>
      <section
        dir={forceLtr ? "ltr" : undefined}
        className="border-t border-blue-500/10 py-8 px-6 bg-[#030014]"
      >
        <div className="max-w-7xl mx-auto">
          <div className="rounded-2xl border border-blue-500/10 bg-[#0f0f23]/40 p-4">
            <div className="max-h-[220px] overflow-y-auto pr-3">
              <BilingualDisclosures
                en={disclosuresEn}
                ar={disclosuresAr}
                englishOnly={forceLtr}
              />
            </div>
          </div>
        </div>
      </section>

      <footer
        dir={layoutRtl ? "rtl" : "ltr"}
        className="border-t border-blue-500/10 py-8 px-6 bg-[#030014]"
      >
        <div
          className={`max-w-7xl mx-auto ${layoutRtl ? "text-right" : "text-left"}`}
        >
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-6">
            <div className="md:col-span-1">
              <Link
                href="/"
                className="flex items-center gap-2 mb-4 hover:opacity-80 transition-opacity"
              >
                <Image
                  src="/logo-04.png"
                  alt="Talaria"
                  width={28}
                  height={28}
                  className="h-7 w-7"
                />
                <span className="text-lg font-bold text-white">Talaria Log</span>
              </Link>
              <p className="text-neutral-500 text-sm mb-4">{t.footer.brandLine}</p>
            </div>

            <div>
              <h4 className="text-white font-semibold mb-4">{t.footer.legal}</h4>
              <ul className="space-y-2">
                <li>
                  <Link
                    href="/privacy"
                    className="text-neutral-400 hover:text-white text-sm"
                  >
                    {t.footer.privacy}
                  </Link>
                </li>
                <li>
                  <Link
                    href="/terms"
                    className="text-neutral-400 hover:text-white text-sm"
                  >
                    {t.footer.terms}
                  </Link>
                </li>
                <li>
                  <Link
                    href="/refunds"
                    className="text-neutral-400 hover:text-white text-sm"
                  >
                    {t.footer.refunds}
                  </Link>
                </li>
                <li>
                  <Link
                    href="/disclaimer"
                    className="text-neutral-400 hover:text-white text-sm"
                  >
                    {t.footer.disclaimer}
                  </Link>
                </li>
                <li>
                  <Link
                    href="/NinjaTrader-disclaimer"
                    className="text-neutral-400 hover:text-white text-sm"
                  >
                    {t.footer.ninjaTraderDisclaimer}
                  </Link>
                </li>
              </ul>
            </div>

            <div>
              <h4 className="text-white font-semibold mb-4">{t.footer.contact}</h4>
              <ul className="space-y-2">
                <li>
                  <a
                    href="mailto:support-center@talaria-log.com"
                    className="text-neutral-400 hover:text-white text-sm"
                  >
                    {t.footer.emailSupport}
                  </a>
                </li>
              </ul>
              <a
                href="mailto:support-center@talaria-log.com"
                className="text-blue-400 hover:text-blue-300 text-sm"
              >
                support-center@talaria-log.com
              </a>
            </div>

            <div>
              <NewsletterSubscribe />
            </div>
          </div>

          <div className="border-t border-blue-500/10 pt-6 flex flex-col md:flex-row items-center justify-between gap-3">
            <p className="text-neutral-500 text-sm">{t.footer.rights}</p>
            <p className="text-neutral-600 text-xs max-w-xl text-center md:text-right">
              {t.footer.riskLine}
            </p>
          </div>
        </div>
      </footer>
    </>
  );
}
