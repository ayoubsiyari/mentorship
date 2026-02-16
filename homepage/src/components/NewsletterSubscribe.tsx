"use client";

import React, { useState } from "react";
import { Mail, Loader2, CheckCircle, AlertCircle } from "lucide-react";
import { useLanguage } from "@/app/LanguageProvider";

export default function NewsletterSubscribe() {
  const { isArabic } = useLanguage();
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<"idle" | "success" | "error">("idle");
  const [message, setMessage] = useState("");

  const t = React.useMemo(
    () =>
      isArabic
        ? {
            title: "اشترك في النشرة الإخبارية",
            subtitle: "احصل على آخر الأخبار والتحديثات",
            emailPlaceholder: "البريد الإلكتروني",
            namePlaceholder: "الاسم (اختياري)",
            subscribe: "اشترك",
            subscribing: "جاري الاشتراك...",
            success: "تم الاشتراك بنجاح!",
            error: "حدث خطأ، يرجى المحاولة مرة أخرى",
          }
        : {
            title: "Subscribe to Newsletter",
            subtitle: "Get the latest news and updates",
            emailPlaceholder: "Email address",
            namePlaceholder: "Name (optional)",
            subscribe: "Subscribe",
            subscribing: "Subscribing...",
            success: "Successfully subscribed!",
            error: "An error occurred, please try again",
          },
    [isArabic]
  );

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim()) return;

    setLoading(true);
    setStatus("idle");
    setMessage("");

    try {
      const res = await fetch("/api/newsletter/subscribe", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: email.trim().toLowerCase(),
          name: name.trim() || null,
          source: "homepage",
        }),
      });

      const data = await res.json();

      if (res.ok && data.success) {
        setStatus("success");
        setMessage(data.message || t.success);
        setEmail("");
        setName("");
      } else {
        setStatus("error");
        setMessage(data.detail || data.message || t.error);
      }
    } catch {
      setStatus("error");
      setMessage(t.error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-full">
      <h4 className="text-white font-semibold mb-2 flex items-center gap-2">
        <Mail className="w-4 h-4 text-blue-400" />
        {t.title}
      </h4>
      <p className="text-neutral-500 text-sm mb-4">{t.subtitle}</p>

      <form onSubmit={handleSubmit} className="space-y-3">
        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder={t.emailPlaceholder}
          required
          className="w-full px-4 py-2.5 rounded-lg bg-white/5 border border-white/10 text-white text-sm placeholder:text-neutral-500 focus:outline-none focus:border-blue-500/50 focus:ring-1 focus:ring-blue-500/25 transition-all"
          dir="ltr"
        />
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder={t.namePlaceholder}
          className="w-full px-4 py-2.5 rounded-lg bg-white/5 border border-white/10 text-white text-sm placeholder:text-neutral-500 focus:outline-none focus:border-blue-500/50 focus:ring-1 focus:ring-blue-500/25 transition-all"
          dir={isArabic ? "rtl" : "ltr"}
        />
        <button
          type="submit"
          disabled={loading || !email.trim()}
          className="w-full px-4 py-2.5 rounded-lg bg-gradient-to-r from-blue-600 to-indigo-600 text-white text-sm font-medium hover:from-blue-500 hover:to-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center justify-center gap-2"
        >
          {loading ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              {t.subscribing}
            </>
          ) : (
            t.subscribe
          )}
        </button>
      </form>

      {status !== "idle" && (
        <div
          className={`mt-3 px-3 py-2 rounded-lg text-sm flex items-center gap-2 ${
            status === "success"
              ? "bg-green-500/10 text-green-400 border border-green-500/20"
              : "bg-red-500/10 text-red-400 border border-red-500/20"
          }`}
        >
          {status === "success" ? (
            <CheckCircle className="w-4 h-4 flex-shrink-0" />
          ) : (
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
          )}
          <span>{message}</span>
        </div>
      )}
    </div>
  );
}
