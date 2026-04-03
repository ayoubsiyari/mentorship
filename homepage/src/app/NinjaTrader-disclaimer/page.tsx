"use client";

import React from "react";
import { motion } from "framer-motion";
import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import Image from "next/image";
import { Button } from "@/components/ui/button";
import SiteDisclosuresFooter from "@/components/SiteDisclosuresFooter";
import {
  ninjaTraderPartnerDisclaimersAr,
  ninjaTraderPartnerDisclaimersEn,
  type NinjaTraderPartnerDisclaimers,
} from "@/content/ninjatraderPartnerDisclaimers";

const copy = {
  en: {
    backHome: "Back Home",
    pageTitle: "NinjaTrader Disclaimer",
    updated: "Last updated: January 2026",
    intro:
      "The following disclosures apply to NinjaTrader® partner content and references on Talaria Log. NinjaTrader® is a registered trademark of NinjaTrader Group, LLC.",
  },
  ar: {
    backHome: "العودة للرئيسية",
    pageTitle: "إخلاء مسؤولية NinjaTrader",
    updated: "آخر تحديث: يناير 2026",
    intro:
      "تنطبق الإخلاءات التالية على محتوى شركاء NinjaTrader® والإشارات إليه على Talaria Log. NinjaTrader® علامة تجارية مسجلة لـ NinjaTrader Group, LLC.",
  },
};

function DisclaimerBody({
  t,
  page,
  dir,
}: {
  t: NinjaTraderPartnerDisclaimers;
  page: (typeof copy)["en"];
  dir: "ltr" | "rtl";
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6 }}
      dir={dir}
      className={dir === "rtl" ? "text-right" : "text-left"}
    >
      <h1 className="text-4xl font-bold text-white mb-4">{page.pageTitle}</h1>
      <p className="text-neutral-400 mb-6">{page.updated}</p>
      <p className="text-neutral-300 leading-relaxed mb-10">{page.intro}</p>

      <h2 className="text-2xl font-semibold text-white mb-6">{t.title}</h2>
      <div className="prose prose-invert max-w-none space-y-8">
        <section>
          <h3 className="text-xl font-semibold text-white mb-3">{t.riskTitle}</h3>
          <p className="text-neutral-300 leading-relaxed">{t.riskText}</p>
        </section>
        <section>
          <h3 className="text-xl font-semibold text-white mb-3">{t.hypoTitle}</h3>
          <p className="text-neutral-300 leading-relaxed">{t.hypoText}</p>
        </section>
        <section>
          <h3 className="text-xl font-semibold text-white mb-3">{t.liveTitle}</h3>
          <p className="text-neutral-300 leading-relaxed">{t.liveText}</p>
        </section>
        <section>
          <h3 className="text-xl font-semibold text-white mb-3">{t.testTitle}</h3>
          <p className="text-neutral-300 leading-relaxed">{t.testText}</p>
        </section>
      </div>
    </motion.div>
  );
}

export default function NinjaTraderDisclaimerPage() {
  return (
    <main className="min-h-screen bg-[#030014]">
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

      <div className="max-w-4xl mx-auto px-6 py-16">
        <DisclaimerBody
          t={ninjaTraderPartnerDisclaimersEn}
          page={copy.en}
          dir="ltr"
        />
        <div className="my-14 h-px bg-white/10" />
        <DisclaimerBody
          t={ninjaTraderPartnerDisclaimersAr}
          page={copy.ar}
          dir="rtl"
        />
      </div>

      <SiteDisclosuresFooter />
    </main>
  );
}
