"use client";

import React from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { SparklesCore } from "@/components/ui/sparkles";
import { Button } from "@/components/ui/button";
import { ArrowLeft } from "lucide-react";
import { useLanguage } from "../LanguageProvider";
import SiteDisclosuresFooter from "@/components/SiteDisclosuresFooter";

function isValidEmail(email: string) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

type CountryDial = {
  name: string;
  dial: string;
  isArab?: boolean;
};

type ParsedRulesItem = {
  n: number;
  label?: string;
  text: string;
  sub?: string[];
};

type ParsedRulesSection = {
  title: string;
  items: ParsedRulesItem[];
};

type ParsedRules = {
  title?: string;
  intro?: string;
  sections: ParsedRulesSection[];
};

function parseArabicRules(lines: string[]): ParsedRules {
  const cleaned = (lines || []).map((l) => (l ?? "").replace(/\uFEFF/g, "")).filter(Boolean);
  const startIndex = cleaned.findIndex((l) => l.includes("إقرار واتفاقية الانتساب"));
  const relevant = startIndex >= 0 ? cleaned.slice(startIndex) : cleaned;

  const title = relevant[0] || "";
  const intro = relevant[1] || "";
  const rest = relevant.slice(2);

  const sections: ParsedRulesSection[] = [];
  let currentSection: ParsedRulesSection | null = null;
  let currentItem: ParsedRulesItem | null = null;
  let n = 1;

  for (const rawLine of rest) {
    const trimmed = (rawLine || "").trim();
    if (!trimmed) continue;

    if (/^(أولاً|ثانياً|ثالثاً|رابعاً|خامساً|سادساً|سابعاً|ثامنًا|ثامناً)/.test(trimmed)) {
      currentSection = { title: trimmed, items: [] };
      sections.push(currentSection);
      currentItem = null;
      continue;
    }

    let content = trimmed;
    if (content.startsWith("•")) {
      content = content.replace(/^•\s*/g, "");
    }

    const subMatch = content.match(/^([أ-ي])\s*[):\-]\s*(.+)$/);
    if (subMatch && currentItem) {
      currentItem.sub = [...(currentItem.sub || []), `${subMatch[1]}) ${subMatch[2].trim()}`];
      continue;
    }

    let label: string | undefined;
    let text = content;
    const colonIndex = content.indexOf(":");
    if (colonIndex > 0 && colonIndex < 48) {
      label = content.slice(0, colonIndex).trim();
      text = content.slice(colonIndex + 1).trim();
    }

    const item: ParsedRulesItem = { n, label, text };
    n += 1;
    currentItem = item;

    if (!currentSection) {
      currentSection = { title: "", items: [] };
      sections.push(currentSection);
    }

    currentSection.items.push(item);
  }

  return { title, intro, sections };
}

function parseEnglishRules(lines: string[]): ParsedRules {
  const cleaned = (lines || []).map((l) => (l ?? "").trim()).filter(Boolean);
  const intro = cleaned[0] || "";
  const rest = cleaned.slice(1);

  const sectionMap = new Map<string, ParsedRulesSection>();
  const sections: ParsedRulesSection[] = [];
  let n = 1;

  for (const raw of rest) {
    const content = (raw || "").trim();
    if (!content) continue;

    const parts = content.split("—");
    const group = parts.length > 1 ? parts[0].trim() : "";
    const remainder = parts.length > 1 ? parts.slice(1).join("—").trim() : content;

    let section = sectionMap.get(group);
    if (!section) {
      section = { title: group, items: [] };
      sectionMap.set(group, section);
      sections.push(section);
    }

    let label: string | undefined;
    let text = remainder;
    const colonIndex = remainder.indexOf(":");
    if (colonIndex > 0 && colonIndex < 60) {
      label = remainder.slice(0, colonIndex).trim();
      text = remainder.slice(colonIndex + 1).trim();
    }

    section.items.push({ n, label, text });
    n += 1;
  }

  return { intro, sections };
}

const COUNTRY_DIALS: CountryDial[] = [
  { name: "Afghanistan", dial: "+93" },
  { name: "Albania", dial: "+355" },
  { name: "Algeria", dial: "+213", isArab: true },
  { name: "Andorra", dial: "+376" },
  { name: "Angola", dial: "+244" },
  { name: "Antigua and Barbuda", dial: "+1" },
  { name: "Argentina", dial: "+54" },
  { name: "Armenia", dial: "+374" },
  { name: "Australia", dial: "+61" },
  { name: "Austria", dial: "+43" },
  { name: "Azerbaijan", dial: "+994" },
  { name: "Bahamas", dial: "+1" },
  { name: "Bahrain", dial: "+973", isArab: true },
  { name: "Bangladesh", dial: "+880" },
  { name: "Barbados", dial: "+1" },
  { name: "Belarus", dial: "+375" },
  { name: "Belgium", dial: "+32" },
  { name: "Belize", dial: "+501" },
  { name: "Benin", dial: "+229" },
  { name: "Bhutan", dial: "+975" },
  { name: "Bolivia", dial: "+591" },
  { name: "Bosnia and Herzegovina", dial: "+387" },
  { name: "Botswana", dial: "+267" },
  { name: "Brazil", dial: "+55" },
  { name: "Brunei", dial: "+673" },
  { name: "Bulgaria", dial: "+359" },
  { name: "Burkina Faso", dial: "+226" },
  { name: "Burundi", dial: "+257" },
  { name: "Cambodia", dial: "+855" },
  { name: "Cameroon", dial: "+237" },
  { name: "Canada", dial: "+1" },
  { name: "Cape Verde", dial: "+238" },
  { name: "Central African Republic", dial: "+236" },
  { name: "Chad", dial: "+235" },
  { name: "Chile", dial: "+56" },
  { name: "China", dial: "+86" },
  { name: "Colombia", dial: "+57" },
  { name: "Comoros", dial: "+269", isArab: true },
  { name: "Congo", dial: "+242" },
  { name: "Costa Rica", dial: "+506" },
  { name: "Croatia", dial: "+385" },
  { name: "Cuba", dial: "+53" },
  { name: "Cyprus", dial: "+357" },
  { name: "Czechia", dial: "+420" },
  { name: "Democratic Republic of the Congo", dial: "+243" },
  { name: "Denmark", dial: "+45" },
  { name: "Djibouti", dial: "+253", isArab: true },
  { name: "Dominica", dial: "+1" },
  { name: "Dominican Republic", dial: "+1" },
  { name: "Ecuador", dial: "+593" },
  { name: "Egypt", dial: "+20", isArab: true },
  { name: "El Salvador", dial: "+503" },
  { name: "Equatorial Guinea", dial: "+240" },
  { name: "Eritrea", dial: "+291" },
  { name: "Estonia", dial: "+372" },
  { name: "Eswatini", dial: "+268" },
  { name: "Ethiopia", dial: "+251" },
  { name: "Fiji", dial: "+679" },
  { name: "Finland", dial: "+358" },
  { name: "France", dial: "+33" },
  { name: "Gabon", dial: "+241" },
  { name: "Gambia", dial: "+220" },
  { name: "Georgia", dial: "+995" },
  { name: "Germany", dial: "+49" },
  { name: "Ghana", dial: "+233" },
  { name: "Greece", dial: "+30" },
  { name: "Grenada", dial: "+1" },
  { name: "Guatemala", dial: "+502" },
  { name: "Guinea", dial: "+224" },
  { name: "Guinea-Bissau", dial: "+245" },
  { name: "Guyana", dial: "+592" },
  { name: "Haiti", dial: "+509" },
  { name: "Honduras", dial: "+504" },
  { name: "Hungary", dial: "+36" },
  { name: "Iceland", dial: "+354" },
  { name: "India", dial: "+91" },
  { name: "Indonesia", dial: "+62" },
  { name: "Iran", dial: "+98" },
  { name: "Iraq", dial: "+964", isArab: true },
  { name: "Ireland", dial: "+353" },
  { name: "Italy", dial: "+39" },
  { name: "Jamaica", dial: "+1" },
  { name: "Japan", dial: "+81" },
  { name: "Jordan", dial: "+962", isArab: true },
  { name: "Kazakhstan", dial: "+7" },
  { name: "Kenya", dial: "+254" },
  { name: "Kiribati", dial: "+686" },
  { name: "Kuwait", dial: "+965", isArab: true },
  { name: "Kyrgyzstan", dial: "+996" },
  { name: "Laos", dial: "+856" },
  { name: "Latvia", dial: "+371" },
  { name: "Lebanon", dial: "+961", isArab: true },
  { name: "Lesotho", dial: "+266" },
  { name: "Liberia", dial: "+231" },
  { name: "Libya", dial: "+218", isArab: true },
  { name: "Liechtenstein", dial: "+423" },
  { name: "Lithuania", dial: "+370" },
  { name: "Luxembourg", dial: "+352" },
  { name: "Madagascar", dial: "+261" },
  { name: "Malawi", dial: "+265" },
  { name: "Malaysia", dial: "+60" },
  { name: "Maldives", dial: "+960" },
  { name: "Mali", dial: "+223" },
  { name: "Malta", dial: "+356" },
  { name: "Marshall Islands", dial: "+692" },
  { name: "Mauritania", dial: "+222", isArab: true },
  { name: "Mauritius", dial: "+230" },
  { name: "Mexico", dial: "+52" },
  { name: "Micronesia", dial: "+691" },
  { name: "Moldova", dial: "+373" },
  { name: "Monaco", dial: "+377" },
  { name: "Mongolia", dial: "+976" },
  { name: "Montenegro", dial: "+382" },
  { name: "Morocco", dial: "+212", isArab: true },
  { name: "Mozambique", dial: "+258" },
  { name: "Myanmar", dial: "+95" },
  { name: "Namibia", dial: "+264" },
  { name: "Nauru", dial: "+674" },
  { name: "Nepal", dial: "+977" },
  { name: "Netherlands", dial: "+31" },
  { name: "New Zealand", dial: "+64" },
  { name: "Nicaragua", dial: "+505" },
  { name: "Niger", dial: "+227" },
  { name: "Nigeria", dial: "+234" },
  { name: "North Korea", dial: "+850" },
  { name: "North Macedonia", dial: "+389" },
  { name: "Norway", dial: "+47" },
  { name: "Oman", dial: "+968", isArab: true },
  { name: "Pakistan", dial: "+92" },
  { name: "Palau", dial: "+680" },
  { name: "Palestine", dial: "+970", isArab: true },
  { name: "Panama", dial: "+507" },
  { name: "Papua New Guinea", dial: "+675" },
  { name: "Paraguay", dial: "+595" },
  { name: "Peru", dial: "+51" },
  { name: "Philippines", dial: "+63" },
  { name: "Poland", dial: "+48" },
  { name: "Portugal", dial: "+351" },
  { name: "Qatar", dial: "+974", isArab: true },
  { name: "Romania", dial: "+40" },
  { name: "Russia", dial: "+7" },
  { name: "Rwanda", dial: "+250" },
  { name: "Saint Kitts and Nevis", dial: "+1" },
  { name: "Saint Lucia", dial: "+1" },
  { name: "Saint Vincent and the Grenadines", dial: "+1" },
  { name: "Samoa", dial: "+685" },
  { name: "San Marino", dial: "+378" },
  { name: "Sao Tome and Principe", dial: "+239" },
  { name: "Saudi Arabia", dial: "+966", isArab: true },
  { name: "Senegal", dial: "+221" },
  { name: "Serbia", dial: "+381" },
  { name: "Seychelles", dial: "+248" },
  { name: "Sierra Leone", dial: "+232" },
  { name: "Singapore", dial: "+65" },
  { name: "Slovakia", dial: "+421" },
  { name: "Slovenia", dial: "+386" },
  { name: "Solomon Islands", dial: "+677" },
  { name: "Somalia", dial: "+252", isArab: true },
  { name: "South Africa", dial: "+27" },
  { name: "South Korea", dial: "+82" },
  { name: "South Sudan", dial: "+211" },
  { name: "Spain", dial: "+34" },
  { name: "Sri Lanka", dial: "+94" },
  { name: "Sudan", dial: "+249", isArab: true },
  { name: "Suriname", dial: "+597" },
  { name: "Sweden", dial: "+46" },
  { name: "Switzerland", dial: "+41" },
  { name: "Syria", dial: "+963", isArab: true },
  { name: "Taiwan", dial: "+886" },
  { name: "Tajikistan", dial: "+992" },
  { name: "Tanzania", dial: "+255" },
  { name: "Thailand", dial: "+66" },
  { name: "Timor-Leste", dial: "+670" },
  { name: "Togo", dial: "+228" },
  { name: "Tonga", dial: "+676" },
  { name: "Trinidad and Tobago", dial: "+1" },
  { name: "Tunisia", dial: "+216", isArab: true },
  { name: "Turkey", dial: "+90" },
  { name: "Turkmenistan", dial: "+993" },
  { name: "Tuvalu", dial: "+688" },
  { name: "Uganda", dial: "+256" },
  { name: "Ukraine", dial: "+380" },
  { name: "United Arab Emirates", dial: "+971", isArab: true },
  { name: "United Kingdom", dial: "+44" },
  { name: "United States", dial: "+1" },
  { name: "Uruguay", dial: "+598" },
  { name: "Uzbekistan", dial: "+998" },
  { name: "Vanuatu", dial: "+678" },
  { name: "Vatican City", dial: "+379" },
  { name: "Venezuela", dial: "+58" },
  { name: "Vietnam", dial: "+84" },
  { name: "Yemen", dial: "+967", isArab: true },
  { name: "Zambia", dial: "+260" },
  { name: "Zimbabwe", dial: "+263" },
];

function applyDialCodeToPhone(prevPhone: string, dial: string) {
  const trimmed = (prevPhone || "").trim();
  if (!trimmed) return `${dial} `;

  if (trimmed.startsWith("+")) {
    const rest = trimmed.replace(/^\+\d+\s*/, "");
    return rest ? `${dial} ${rest}` : `${dial} `;
  }

  return `${dial} ${trimmed}`;
}

function ensureDialPrefix(nextValue: string, dial: string) {
  const prefix = `${dial} `;
  const value = nextValue || "";

  if (!dial) return value;
  if (value === dial) return prefix;
  if (value.startsWith(prefix)) return value;
  if (value.startsWith(dial)) {
    const rest = value.slice(dial.length).replace(/^\s*/, "");
    return `${dial} ${rest}`;
  }

  if (!value.trim()) return prefix;
  if (value.trim().startsWith("+")) {
    const rest = value.trim().replace(/^\+\d+\s*/, "");
    return rest ? `${dial} ${rest}` : prefix;
  }

  return `${dial} ${value.trim()}`;
}

function isValidPhone(phone: string, dial: string) {
  if (!dial) return false;
  const compactDial = dial.replace(/\s+/g, "");
  const compact = (phone || "").replace(/\s+/g, "");
  if (!compact.startsWith(compactDial)) return false;
  if (!/^\+\d{7,15}$/.test(compact)) return false;
  if (compact === compactDial) return false;
  return true;
}

export default function RegisterPage() {
  const { isArabic } = useLanguage();
  const [authChecked, setAuthChecked] = React.useState(false);
  const [isAuthed, setIsAuthed] = React.useState(false);

  React.useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch("/api/auth/me", { credentials: "include", cache: "no-store" });
        const data = await res.json().catch(() => null);
        const user = data && (data as any).user;
        const authed = Boolean(res.ok && user && typeof user.id === "number");
        if (!cancelled) {
          setIsAuthed(authed);
          setAuthChecked(true);
        }
        if (!cancelled && authed && user) {
          const nextName = typeof user.name === "string" ? user.name : "";
          const nextEmail = typeof user.email === "string" ? user.email : "";
          setFullName(nextName);
          setEmail(nextEmail);
          if (typeof user.phone === "string" && user.phone) {
            setPhone(user.phone);
          }
          if (typeof user.country === "string" && user.country) {
            setCountry(user.country);
            setCountryQuery(user.country);
          }
        }
        if (!authed) {
          window.location.href = "/login/?mode=signin&next=/register/";
        }
      } catch {
        if (!cancelled) {
          setIsAuthed(false);
          setAuthChecked(true);
        }
        window.location.href = "/login/?mode=signin&next=/register/";
      }
    })();

    return () => {
      cancelled = true;
    };
  }, []);
  const t = React.useMemo(
    () =>
      isArabic
        ? {
            page: {
              title: "تسجيل المِنتورشيب",
              intro:
                "املأ بياناتك للتقديم على مِنتورشيب Talaria. سنراجع الطلب ونتواصل معك.",
              rulesTitle: "القواعد والشروط",
              rules: [
                "تعد هذه الاستمارة بمثابة اتفاق مكتوب يُوضِح التزامات تالاريا وفريقها تجاه المُنتسبين للمِنتورشيب. ومن ناحية أُخرى تُوضِح الواجبات المُترتبة على المُنتسبين للمِنتورشيب. وبمُجرَّد إجابتك وإرسالك لهذه الاستمارة فهذا يُعتبر إقرارًا من المُرسِل بالموافقة على جميع ما يلي:",
                "\t•\tيتوجّب على جميع المنتسبين للمِنتورشيب قراءة واستيعاب \"تنويه بالمخاطر وإخلاء المسؤولية\" على الموقع الرسمي ل تلاريا.",
                "",
                "\t•\tيُقِرّ المنتسبون بعلمهم التام بأن جميع الخدمات التعليمية المُقدّمة والاستشارات في برنامج المِنتورشيب المُقدّمة من قبل تالاريا إلى المنتسبين لا تُؤدّي إلى أي مسؤولية على تالاريا وفريقها عن أفعال المنتسبين وقراراتهم الاستثمارية أثناء أو بعد انتهاء المِنتورشيب لكون تالاريا تقدّم خدمة تدريبية فقط وهي غير مُلزَمة أو مُوجَّهة للمنتسبين في اتخاذ قرارات أو أفعال من شأنها تحقيق أي خسائر أو خلافه وتعدّ كافة المسؤوليات القانونية وغيرها مسؤولية المنتسبين فقط عن أي أعمال يقومون بها مُرتبطة كانت أو غير مُرتبطة بالخدمات المُقدّمة ويُقرّ المنتسبون بإخلاء مسؤولية تالاريا وفريقها عن مضمون ما سبق. ولا يجوز لهم المطالبة بأي أموال، أو تعويضات، أو أي شيء مادي، أو قانوني.",
                "",
                "\t•\tتحيط تالاريا وفريقها علم جميع المنتسبين بأن تداول الفوركس والأسهم والعقود الآجلة والعملات الرقمية لها أخطار جسيمة والتي يمكن أن تؤدي إلى خسائر كبيرة برأس المال في حالة التداول بدون علم كافٍ وتنفي تالاريا وفريقها مسؤوليتهم عن هذه المخاطر والخسائر لكونهم غير مسؤولين عن أفعال المنتسبين أثناء المِنتورشيب وبعدها. وتُعد الموافقة على هذه الاستمارة إقرارًا من المنتسبين بإخلاء مسؤولية تالاريا وفريقها عن أي خسائر.",
                "",
                "\t•\tهذه المنتورشيب هي لمن يريد تعلم وتطبيق الـ ICT وفقًا لما تم شرحه في الكورس المجاني على اليوتيوب. بناءً على هذا، نحتفظ بحقنا في الالتزام بالمعلومات المذكورة بالكورس أو التوسع بها وفقًا لما نراه مناسبًا ولسنا ملزمين بالتعليق أو تقديم شروحات حول ما يقدمه غيرنا من مدارس أو أساليب تحليل أخرى.",
                "",
                "",
                "\t•\tتشمل المنتورشيب بثوثًا بما لا يقل عن ساعتين يوميًا لمدة خمسة أيام في الأسبوع على مدى أربعة أسابيع ( من الساعة 9 مساء حتى الساعة 12 بتوقيت مكة المكرمة) بالإضافة إلى إدارة للسيرفر لمدة 12 ساعة من 24 ساعة في اليوم بالإضافة إلى تواصل صوتي مباشر مع المدرب (هيرمس) وفريقه. ونتعهد بالإجابة على أي تساؤل من ضمن معلومات المنتورشيب والكورس المجاني خلال مدة لا تتعدى 24 ساعة.",
                "",
                "",
                "\t•\tتتضمن المنتورشيب مواد فيديو وملفات مكتوبة و أدوات أخرى من مؤشرات و غيرها، وسيتم توزيعها على المنتسبين وفقًا للخطة الخاصة بالمنتورشيب ولا يجوز للمنتسبين المطالبة بتغيير الترتيب المخصص لهذه المواد.",
                "",
                "",
                "\t•\tهذه المنتورشيب خاصة لمن يريد تطوير نفسه من ناحية تنفيذ الصفقات وعليه:",
                "أ) المنتسبون هم المطالبون بتنفيذ الصفقات واتخاذ القرارات بأنفسهم، وتالاريا وفريقها لا يقدمون أي تعهد بتقديم توصيات أو تحليلات إذا لم يجدوا لذلك داعٍ.",
                "ب) تالاريا  وفريقها لا يقدمون أي ضمانات بنجاح صفقات المشتركين أو تحقيقهم للأرباح نظرًا لوجود فيصل بين النجاح والفشل في هذا المجال، وهذا الفيصل هو الطالب نفسه وقدرته على التنفيذ واتخاذ القرار.",
                "ج) تالاريا  وفريقها يتحفظون على الإجابة على الأسئلة المكررة، وسيتم إحالة السائل إلى قسم الأسئلة المكررة لتجنب إضاعة الوقت والتركيز على مشاكل الطلاب التي تتطلب احتكاكًا مباشرًا مع المدرب.",
                "\t•\tالمدة المقررة للمنتورشيب هي أربعة أسابيع ابتداءً من 6 يوليو 2025 ولغاية 31 يوليو 2026، ولكن:",
                "أ) نحتفظ بحق تأجيل موعد البداية بما لا يتجاوز ثلاثين يومًا في حالة الظروف القاهرة، ونتعهد بإعادة جميع مبالغ الاشتراكات في حال زادت مدة التأجيل عن ثلاثين يومًا.",
                "ب) في حالة حدوث ظروف قاهرة أدت إلى انقطاع المنتورشيب بعد انطلاقها، فنتعهد بإعادة جميع مبالغ الاشتراكات في حال زادت المدة عن 15 يومًا، مع التأكيد على أن المدة الكلية للمنتورشيب ستبقى أربعة أسابيع في حال الانقطاع.",
                "ج) لا يحق للمشتركين المطالبة بتقديم موعد بداية المنتورشيب عن الموعد المقرر.",
                "",
                "\t•\tسيتم متابعة الحضور باستخدام برنامج خاص تفاديًا لأي شكاوى من غير الملتزمين، ولسنا ملزمين بتسجيل أي بث مباشر إذا لم نر لذلك حاجة.",
                "",
                "\t•\tجميع المواد التي سيتم مشاركتها مع المنتسبين هي ملكية خاصة لتالاريا وسيتم حمايتها إما برمز سري أو بكود تتبع، وفي حال تسريب أي من المحتوى الموزع على المنتسبين سيتم إبعاد من قام بالتسريب بدون أي تحذير وسيفقد حقه في استرداد مبلغ الاشتراك.",
                "",
                "\t•\tنحن غير مسؤولون عن تحقيق مدى قانونية الاستثمار والتداول والأصول المسموح بالتعامل بها في منطقة المنتسبين الجغرافية وتقع كامل المسؤولية على المنتسبين في التحقق من قوانين بلدان إقامتهم حول موضوع الاستثمار والتداول والأصول المصرح بها.",
                "",
                "\t•\tجميع المواد التي يتم مشاركتها من قبل تالاريا وفريقها والمنتسبين للمنتورشيب، سواء كانت في الغرف العامة أو في الرسائل الخاصة، هي ملك لتالاريا ومن حقنا التصرف بها دون أي مساءلة.",
                "",
                "\t•\tيلتزم المنتسبون بالتعامل المباشر مع تالاريا وفريقها فقط بدون أن يكون لهم أي عضويات أخرى في أي أكاديميات أخرى من التي تقدم خدمات تداول. وفي حالة تعامل أحد المنتسبين مع أكاديميات أخرى أو مزودي خدمات آخرين دون علمنا، يحق لنا إنهاء التعاقد وإغلاق العضوية دون استرداد رسوم الاشتراك.",
                "",
                "",
                "\t•\tيلتزم المنتسبون بعدم استخدام المعلومات المقدمة من قبل تالاريا في أي نشاط، ولا يجوز للمنتسبين التربح المادي من الخدمات المقدمة من تالاريا وفريقها إلا من خلال حساب التداول الخاص بالمنتسبين فقط.",
                "",
                "\t•\tقام هرميس بتقديم كورس مجاني ومتاح للجميع على اليوتيوب، وننصحك بشدة بمتابعته والتدرب على محتواه كي تكون قادرًا على الاعتماد على نفسك دون الحاجة إلى المنتورشيب. وبناءً على ذلك، نرجو من جميع المنتسبين أخذ وقتهم الكافي لاتخاذ قرار الانتساب للمنتورشيب بعد تأكدهم من حاجتهم لها.",
                "",
                "\t•\tنظرًا للإقبال الشديد على المنتورشيب، سيتم إغلاق باب القبول حال اكتمال العدد الذي نرى أننا قادرون على إدارته وتقديم أفضل ما لدينا له، ونمتنع عن قبول أي شخص بعد إغلاق باب القبول.",
                "",
                "\t•\tيقر المنتسب بأنه بمجرد ملء هذه الاستمارة وإرسالها عبر البريد الإلكتروني الخاص به، فإنه موافق على شروط الانتساب وتعد موافقة نهائية من قبل المنتسب يعتد بها أمام المحاكم، ولا يجوز الجحود أو الطعن بها، وتسري كافة البنود والحقوق بمجرد الإرسال ويطبق عليها القانون.",
                "",
                "\t•\tسيتم الرد على طلبات التقديم بشكل دوري، وسيتلقى المتقدمون الرد خلال فترة زمنية لا تزيد عن 72 ساعة من بريدنا الإلكتروني الرسمي (info@talaria-log.com) مع تفاصيل الدفع بالعملات الرقمية فقط.",
                "إقرار واتفاقية الانتساب لبرنامج \"تالاريا مِنتورشيب\"",
                "تُعد هذه الاستمارة اتفاقاً مكتوباً يُحدد الالتزامات المتبادلة بين فريق تالاريا والمنتسبين لبرنامج المِنتورشيب. يُعتبر إرسالك لهذه الاستمارة إقراراً صريحاً بالموافقة على البنود التالية:",
                "أولاً: إخلاء المسؤولية والمخاطر",
                "\t•\tالاطلاع والوعي: يتعهد المنتسب بقراءة واستيعاب \"تنويه المخاطر وإخلاء المسؤولية\" المتاح على موقع تالاريا الرسمي.",
                "\t•\tطبيعة الخدمة: يقر المنتسب بأن جميع الخدمات المُقدمة هي خدمات تعليمية وتدريبية فقط. ولا تتحمل تالاريا أو فريقها أي مسؤولية قانونية أو مالية عن قرارات المنتسب الاستثمارية أو نتائجه المالية (ربحاً أو خسارة) أثناء أو بعد فترة البرنامج.",
                "\t•\tمخاطر التداول: يدرك المنتسب أن التداول في الفوركس، الأسهم، العقود الآجلة، والعملات الرقمية ينطوي على مخاطر جسيمة قد تؤدي لفقدان رأس المال. وبناءً عليه، تسقط أي مطالبة مالية أو قانونية تجاه تالاريا ناتجة عن هذه المخاطر.",
                "\t•\tالقوانين المحلية: تقع على عاتق المنتسب مسؤولية التحقق من قانونية التداول والأصول المالية في بلده؛ وتخلي تالاريا مسؤوليتها عن أي مخالفات قانونية تتعلق بنطاق إقامة المنتسب.",
                "ثانياً: المنهج التعليمي وآلية العمل",
                "\t•\tمنهجية: ICT البرنامج مخصص لتعلم وتطبيق منهجية  ICT كما شُرِحت في الكورس المجاني. تحتفظ تالاريا بحق الالتزام بهذا المنهج أو التوسع فيه، ولا تلتزم بتقديم شروحات لمدارس تحليلية أخرى.",
                "\t•\tالجدول الزمني والدعم: يتضمن البرنامج بثاً مباشراً (ساعتين يومياً/5 أيام أسبوعياً) من الساعة 9 مساءً وحتى 11 ليلا بتوقيت مكة المكرمة. كما تلتزم تالاريا بإدارة السيرفر لمدة 12 ساعة يومياً والرد على الاستفسارات الفنية خلال 24 ساعة كحد أقصى.",
                "\t•\tالمواد التعليمية: سيتم توزيع الفيديوهات والملفات والأدوات وفق خطة زمنية محددة، ولا يحق للمنتسب المطالبة بتغيير ترتيب عرض المواد.",
                "\t•\tالاستقلالية في التنفيذ: يلتزم المنتسب باتخاذ قراراته وتنفيذ صفقاته بنفسه. لا تضمن تالاريا نجاح الصفقات، ولها الحق في عدم تقديم توصيات أو تحليلات مباشرة إذا لم ترَ حاجة لذلك.",
                "ثالثاً: المواعيد والظروف القاهرة",
                "\t•\tفترة البرنامج: تبدأ المِنتورشيب من 6  يوليو 2026 و تستمر لمدة اربعة اسابيع متتالية",
                "\t•\tأ: يحق لتالاريا تأجيل البداية لمدة لا تتجاوز 30 يوماً للظروف القاهرة، مع الالتزام برد الرسوم كاملة إذا تجاوز التأجيل هذه المدة.",
                "\t•\tب: في حال توقف البرنامج لظروف قاهرة لمدة تزيد عن 15 يوماً بعد بدئه، يتم رد الرسوم، مع التأكيد على أن مدة التعلم الفعلية تظل 4 أسابيع.",
                "\t•\tالحضور والتسجيل: سيتم تتبع الحضور عبر برنامج خاص، ولا تلتزم تالاريا بتسجيل البث المباشر إلا وفقاً لما تراه مناسباً.",
                "رابعاً: الملكية الفكرية والالتزام السلوكي",
                "\t•\tحقوق الملكية: جميع المواد (فيديوهات، ملفات، أكواد) هي ملكية حصرية لتالاريا. أي تسريب للمحتوى يؤدي إلى استبعاد العضو فوراً وحرمانه من حق استرداد الرسوم، مع ملاحقته قانونياً.",
                "\t•\tالحصرية: يلتزم المنتسب بعدم الانضمام لأكاديميات تداول أخرى أثناء فترة البرنامج. وفي حال ثبت خلاف ذلك، يحق لتالاريا إنهاء اشتراكه دون رد الرسوم.",
                "\t•\tالاستخدام الشخصي: تُستخدم المعلومات المُقدمة للتداول الشخصي فقط، ويُحظر استخدامها في أي نشاط تجاري أو تربح مادي خارج حساب التداول الخاص بالمنتسب.",
                "\t•\tالمحتوى التفاعلي: جميع ما يتم مشاركته في الغرف العامة أو الرسائل الخاصة يصبح ملكاً لتالاريا ويحق لها التصرف به.",
                "خامساً: القبول والتسجيل",
                "\t•\tالقرار المستنير: ننصح بمتابعة الكورس المجاني على يوتيوب أولاً، وعلى المنتسب التأكد من حاجته الفعليه للمنتورشيب قبل التسجيل. الرسوم غير قابلة للاسترداد الا في حالة الغاء اقامة المنتورشيب او تعذر تالاريا عن تنفيذ التزاماتها المذكورة اعلاه.",
                "\t•\tاكتمال العدد: يتم إغلاق باب القبول فور اكتمال العدد المحدد لضمان جودة الإدارة، ولا تُقبل أي طلبات إضافية بعدها.",
                "\t•\tحجية الاتفاق: يعتبر ملء هذه الاستمارة وإرسالها موافقة نهائية و ملزمة ، ولا يجوز الطعن فيها.",
                "\t•\tآلية الرد: يتم الرد على الطلبات خلال 72 ساعة عبر البريد الرسمي (support-center@talaria-log.com) ، مع تفاصيل الدفع (بالعملات الرقمية فقط).",
              ],
              rulesNote:
                "بإرسال هذه الاستمارة، فأنت تقر بموافقتك على البنود أعلاه وتقبل سياساتنا القانونية.",
              rulesChoiceHint:
                "يرجى قراءة القواعد والشروط كاملة ثم اختر موافق أو غير موافق لإكمال التسجيل.",
              rulesAgree: "موافق",
              rulesDisagree: "غير موافق",
              rulesAgreeNote: "شكراً لك. يمكنك الآن إكمال التسجيل.",
              rulesDisagreeNote:
                "عذراً، لا يمكنك إكمال التسجيل بدون الموافقة على القواعد والشروط.",
              rulesGateTitle: "الموافقة مطلوبة",
              rulesGatePrompt:
                "يرجى قراءة القواعد والشروط بالأعلى ثم اختيار موافق أو غير موافق للمتابعة.",
              legal: "",
              terms: "الشروط",
              privacy: "الخصوصية",
              disclaimer: "إخلاء المسؤولية",
            },
            form: {
              fullName: "الاسم الكامل",
              email: "البريد الإلكتروني",
              country: "الدولة",
              countrySearchPh: "ابحث عن دولة",
              phone: "رقم الهاتف",
              age: "العمر",
              telegram: "تيليجرام",
              discord: "ديسكورد",
              instagram: "انستغرام",
              fullNamePh: "الاسم الكامل",
              emailPh: "you@example.com",
              countrySelect: "اختر دولة",
              arabicCountries: "الدول العربية",
              allCountries: "كل الدول",
              phoneSelectFirst: "اختر الدولة أولاً",
              agePh: "عمرك",
              telegramPh: "@username",
              discordPh: "اسم مستخدم ديسكورد",
              instagramPh: "@instagram",
              agreeRules: "أوافق على القواعد والشروط.",
              agreeTermsA: "أوافق على ",
              agreeTermsB: "الشروط",
              agreeTermsC: " و ",
              agreeTermsD: "سياسة الخصوصية",
              submit: "إرسال التسجيل",
              submitting: "جارٍ الإرسال...",
              saving: "جارٍ الحفظ...",
              backToBootcamp: "العودة إلى المِنتورشيب",
              note:
                "هذا النموذج مخصص لتسجيل المِنتورشيب. سنتواصل معك عبر البريد الإلكتروني.",
            },
            validation: {
              fullNameRequired: "الاسم الكامل مطلوب",
              emailInvalid: "يرجى إدخال بريد إلكتروني صحيح",
              countryRequired: "الدولة مطلوبة",
              phoneRequired: "رقم الهاتف مطلوب",
              phoneInvalid: "يرجى إدخال رقم هاتف صحيح",
              ageRequired: "العمر مطلوب",
              ageInvalid: "يرجى إدخال عمر صحيح",
              ageUnder18Title: "عذراً، لا يمكن التسجيل لمن هم دون 18 عاماً.",
              ageUnder18Text:
                "التداول في الفوركس/الأسهم/العقود الآجلة والعملات الرقمية ينطوي على مخاطر عالية وقد يؤدي إلى خسارة رأس المال. كما أن اتخاذ قرارات مالية والتزام الشروط القانونية يتطلب مسؤولية ونضجاً مناسبين. لهذا السبب، هذا البرنامج مخصص لمن هم بعمر 18 عاماً أو أكثر.",
              telegramRequired: "تيليجرام مطلوب",
              discordRequired: "ديسكورد مطلوب",
              instagramRequired: "انستغرام مطلوب",
              acceptRules: "يجب الموافقة على قواعد المِنتورشيب",
              acceptTerms: "يجب الموافقة على الشروط والخصوصية",
            },
            submit: {
              failed: "فشل التسجيل",
              failedTryAgain: "فشل التسجيل. حاول مرة أخرى.",
            },
            success: {
              title: "تم إرسال التسجيل",
              thanksA: "شكراً، ",
              thanksB: " سنتواصل معك عبر ايميلك ",
              checkEmail:
                "يرجى التحقق من صندوق البريد (وأيضاً مجلد الرسائل غير المرغوب فيها)",
              summary: "ملخص (محلي فقط):",
              country: "الدولة:",
              age: "العمر:",
              phone: "الهاتف:",
              telegram: "تيليجرام:",
              discord: "ديسكورد:",
              instagram: "انستغرام:",
            },
          }
        : {
            page: {
              title: "Bootcamp Registration",
              intro:
                "Fill in your details to apply for the Talaria Bootcamp. We’ll review and contact you.",
              rulesTitle: "Rules & Conditions",
              rules: [
                "This form constitutes a written agreement that outlines the mutual obligations between the Talaria team and the participants of the Mentorship Program. By submitting this form, you expressly acknowledge and agree to the following terms:",
                "Risk & liability — Awareness: You undertake to read and understand the \"Risk Notice & Disclaimer\" available on Talaria’s official website.",
                "Risk & liability — Nature of service: You acknowledge that all services provided are educational/training only. Talaria and its team assume no legal or financial responsibility for your investment decisions or financial results (profit or loss) during or after the program.",
                "Risk & liability — Trading risks: You understand that trading forex, stocks, futures, and cryptocurrencies involves substantial risks that may lead to loss of capital. Accordingly, any financial or legal claims against Talaria arising from such risks are waived.",
                "Risk & liability — Local laws: You are responsible for verifying the legality of trading and permitted instruments in your country/region; Talaria disclaims any liability for violations related to your jurisdiction.",
                "Curriculum & delivery — Methodology (ICT): The program is intended to learn and apply the ICT methodology as explained in the free course. Talaria reserves the right to adhere to this curriculum or expand it, and is not obligated to provide commentary on other analytical schools or approaches.",
                "Curriculum & delivery — Schedule & support: The program includes live streams of at least 2 hours per day / 5 days per week for 4 weeks (9:00 PM–12:00 AM Makkah time). Talaria also commits to managing the server for 12 hours per day and responding to inquiries within a maximum of 24 hours.",
                "Curriculum & delivery — Educational materials: Videos, written files, indicators, and other tools will be distributed according to the program plan. You may not request changes to the designated order of these materials.",
                "Curriculum & delivery — Independence in execution: You commit to making your own decisions and executing your own trades. Talaria does not guarantee trade success, and may choose not to provide direct recommendations or analysis unless deemed necessary.",
                "Program dates & force majeure — Program period: The mentorship is scheduled from 6 July 2025 until 31 July 2026.",
                "Program dates & force majeure — Talaria may postpone the start date by no more than 30 days in cases of force majeure, with a full refund if the delay exceeds 30 days.",
                "Program dates & force majeure — If the program is suspended after it begins for more than 15 days due to force majeure, fees will be refunded, while the total learning duration remains 4 weeks.",
                "Program dates & force majeure — Attendance & recordings: Attendance will be tracked via a dedicated system. Talaria is not obligated to record live sessions unless deemed necessary.",
                "Intellectual property & conduct — IP rights: All materials (videos, files, code) are Talaria’s exclusive property. Any leak of distributed content results in immediate removal and forfeiture of refund rights, and may result in legal action.",
                "Intellectual property & conduct — Exclusivity: You agree not to join other trading academies/providers during the program. If otherwise proven, Talaria may terminate your membership without refund.",
                "Intellectual property & conduct — Personal-use only: The information provided is for personal trading only and may not be used for any commercial activity or monetized outside your own trading account.",
                "Intellectual property & conduct — Interactive content: Anything shared in public rooms or private messages by Talaria, its team, or participants becomes Talaria’s property and may be used at Talaria’s discretion.",
                "Acceptance & registration — Informed decision: We strongly recommend following the free YouTube course first and ensuring you truly need the mentorship before enrolling.",
                "Acceptance & registration — Capacity: Admissions will close once capacity is reached to ensure quality. No additional applications will be accepted after closure.",
                "Acceptance & registration — Binding agreement: Submitting this form constitutes final and legally binding acceptance. It may be relied upon in court and may not be contested.",
                "Acceptance & registration — Response: Applications are reviewed periodically. You will receive a reply within 72 hours from our official email (support-center@talaria-log.com) with crypto-only payment details.",
              ],
              rulesNote:
                "By submitting this form, you confirm your acceptance of the terms above and our legal policies.",
              rulesChoiceHint:
                "Please read the Rules & Conditions, then choose Agree or Disagree to continue.",
              rulesAgree: "Agree",
              rulesDisagree: "Disagree",
              rulesAgreeNote: "Thank you. You can now continue your registration.",
              rulesDisagreeNote:
                "Sorry, you can’t complete the registration without agreeing to the Rules & Conditions.",
              rulesGateTitle: "Agreement required",
              rulesGatePrompt:
                "Please read the Rules & Conditions above, then choose Agree or Disagree to proceed.",
              legal: "Legal:",
              terms: "Terms",
              privacy: "Privacy",
              disclaimer: "Disclaimer",
            },
            form: {
              fullName: "Full name",
              email: "Email",
              country: "Country",
              countrySearchPh: "Search country",
              phone: "Phone",
              age: "Age",
              telegram: "Telegram",
              discord: "Discord",
              instagram: "Instagram",
              fullNamePh: "John Doe",
              emailPh: "you@example.com",
              countrySelect: "Select a country",
              arabicCountries: "Arabic countries",
              allCountries: "All countries",
              phoneSelectFirst: "Select country first",
              agePh: "Your age",
              telegramPh: "@username",
              discordPh: "Your Discord username",
              instagramPh: "@instagram",
              agreeRules: "I agree to the Rules & Conditions.",
              agreeTermsA: "I agree to the ",
              agreeTermsB: "Terms",
              agreeTermsC: " and ",
              agreeTermsD: "Privacy Policy",
              submit: "Submit registration",
              submitting: "Submitting...",
              saving: "Saving...",
              backToBootcamp: "Back to Bootcamp",
              note:
                "This registration form is for Bootcamp enrollment. We will contact you by email.",
            },
            validation: {
              fullNameRequired: "Full name is required",
              emailInvalid: "Please enter a valid email",
              countryRequired: "Country is required",
              phoneRequired: "Phone is required",
              phoneInvalid: "Please enter a valid phone number",
              ageRequired: "Age is required",
              ageInvalid: "Please enter a valid age",
              ageUnder18Title: "Sorry, you can’t register if you are under 18.",
              ageUnder18Text:
                "Trading forex/stocks/futures/crypto involves high risk and can result in loss of capital. It also requires legal responsibility and mature decision-making around financial risk. For these reasons, this program is only available to participants aged 18 or older.",
              telegramRequired: "Telegram is required",
              discordRequired: "Discord is required",
              instagramRequired: "Instagram is required",
              acceptRules: "You must accept the Bootcamp rules",
              acceptTerms: "You must accept the Terms & Privacy",
            },
            submit: {
              failed: "Registration failed",
              failedTryAgain: "Registration failed. Please try again.",
            },
            success: {
              title: "Registration submitted",
              thanksA: "Thanks, ",
              thanksB: ". We received your request and will contact you at ",
              checkEmail:
                "Please check your email inbox (and spam folder) for updates.",
              summary: "Summary (local only):",
              country: "Country:",
              age: "Age:",
              phone: "Phone:",
              telegram: "Telegram:",
              discord: "Discord:",
              instagram: "Instagram:",
            },
          },
    [isArabic]
  );

  const [fullName, setFullName] = React.useState("");
  const [email, setEmail] = React.useState("");
  const [phone, setPhone] = React.useState("");
  const [country, setCountry] = React.useState("");
  const [countryQuery, setCountryQuery] = React.useState("");
  const [countryDropdownOpen, setCountryDropdownOpen] = React.useState(false);
  const countryDropdownRef = React.useRef<HTMLDivElement | null>(null);
  const [age, setAge] = React.useState("");
  const [telegram, setTelegram] = React.useState("");
  const [discord, setDiscord] = React.useState("");
  const [instagram, setInstagram] = React.useState("");
  const [agreeTerms, setAgreeTerms] = React.useState(false);
  const [rulesDecision, setRulesDecision] = React.useState<"agree" | "disagree" | null>(null);
  const [ageRejected, setAgeRejected] = React.useState(false);

  const [errors, setErrors] = React.useState<Record<string, string>>({});
  const [submitted, setSubmitted] = React.useState(false);
  const [isSubmitting, setIsSubmitting] = React.useState(false);
  const [submitError, setSubmitError] = React.useState("");

  React.useEffect(() => {
    if (!ageRejected) return;
    const n = Number((age || "").trim());
    if (Number.isFinite(n) && n >= 18) {
      setAgeRejected(false);
      setErrors((prev) => {
        if (prev.age !== t.validation.ageUnder18Title) return prev;
        const next = { ...prev };
        delete next.age;
        return next;
      });
    }
  }, [age, ageRejected, t.validation.ageUnder18Title]);

  const dialByCountry = React.useMemo(() => {
    return new Map(COUNTRY_DIALS.map((c) => [c.name, c.dial] as const));
  }, []);

  const arabCountries = React.useMemo(() => {
    return COUNTRY_DIALS
      .filter((c) => c.isArab)
      .slice()
      .sort((a, b) => a.name.localeCompare(b.name));
  }, []);

  const otherCountries = React.useMemo(() => {
    return COUNTRY_DIALS
      .filter((c) => !c.isArab)
      .slice()
      .sort((a, b) => a.name.localeCompare(b.name));
  }, []);

  const filteredArabCountries = React.useMemo(() => {
    const q = (countryQuery || "").trim().toLowerCase();
    if (!q) return arabCountries;
    return arabCountries.filter((c) => {
      const name = c.name.toLowerCase();
      if (name.startsWith(q)) return true;
      return name.split(/\s+/).some((part) => part.startsWith(q));
    });
  }, [arabCountries, countryQuery]);

  const filteredOtherCountries = React.useMemo(() => {
    const q = (countryQuery || "").trim().toLowerCase();
    if (!q) return otherCountries;
    return otherCountries.filter((c) => {
      const name = c.name.toLowerCase();
      if (name.startsWith(q)) return true;
      return name.split(/\s+/).some((part) => part.startsWith(q));
    });
  }, [otherCountries, countryQuery]);

  const selectedDial = React.useMemo(() => {
    return dialByCountry.get(country) || "";
  }, [country, dialByCountry]);

  const onCountryChange = (value: string) => {
    setCountry(value);
    setCountryQuery(value);
    setCountryDropdownOpen(false);
    const dial = dialByCountry.get(value);
    if (dial) {
      setPhone((prev) => applyDialCodeToPhone(prev, dial));
    }
  };

  React.useEffect(() => {
    if (!countryDropdownOpen) return;

    const onPointerDown = (e: MouseEvent | TouchEvent) => {
      const targetNode = e.target as Node | null;
      if (!countryDropdownRef.current || !targetNode) return;
      if (!countryDropdownRef.current.contains(targetNode)) {
        setCountryDropdownOpen(false);
      }
    };

    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") setCountryDropdownOpen(false);
    };

    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("touchstart", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("touchstart", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [countryDropdownOpen]);

  const validate = () => {
    const next: Record<string, string> = {};
    let under18 = false;

    if (!fullName.trim()) next.fullName = t.validation.fullNameRequired;
    if (!email.trim() || !isValidEmail(email.trim())) next.email = t.validation.emailInvalid;
    if (!country.trim()) next.country = t.validation.countryRequired;
    // Only validate phone if user entered more than just the dial code
    const phoneCompact = (phone || "").replace(/\s+/g, "");
    const dialCompact = (selectedDial || "").replace(/\s+/g, "");
    const hasRealPhone = phoneCompact && dialCompact && phoneCompact !== dialCompact;
    if (hasRealPhone && !isValidPhone(phone.trim(), selectedDial)) next.phone = t.validation.phoneInvalid;
    if (!age.trim()) next.age = t.validation.ageRequired;
    if (age.trim() && (!Number.isFinite(Number(age.trim())) || Number(age.trim()) <= 0)) next.age = t.validation.ageInvalid;
    if (
      age.trim() &&
      Number.isFinite(Number(age.trim())) &&
      Number(age.trim()) > 0 &&
      Number(age.trim()) < 18
    ) {
      next.age = t.validation.ageUnder18Title;
      under18 = true;
    }
    if (!discord.trim()) next.discord = t.validation.discordRequired;
    if (rulesDecision !== "agree") next.rulesDecision = t.validation.acceptRules;
    if (!agreeTerms) next.agreeTerms = t.validation.acceptTerms;

    setAgeRejected(under18);
    setErrors(next);
    return Object.keys(next).length === 0;
  };

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate()) return;

    setIsSubmitting(true);
    setSubmitError("");
    try {
      // Only send phone if it's more than just the dial code
      const submitPhoneCompact = (phone || "").replace(/\s+/g, "");
      const submitDialCompact = (selectedDial || "").replace(/\s+/g, "");
      const hasSubmitPhone = submitPhoneCompact && submitDialCompact && submitPhoneCompact !== submitDialCompact;
      const res = await fetch("/api/bootcamp/register", {
        credentials: "include",
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          full_name: fullName,
          email,
          ...(hasSubmitPhone ? { phone } : {}),
          country,
          age: Number(age),
          ...(telegram.trim() ? { telegram } : {}),
          discord,
          ...(instagram.trim() ? { instagram } : {}),
          agree_terms: agreeTerms,
          agree_rules: rulesDecision === "agree",
        }),
      });

      if (res.status === 401) {
        window.location.href = "/login/?mode=signin&next=/register/";
        return;
      }

      if (!res.ok) {
        let detail = t.submit.failed;
        try {
          const data = await res.json();
          if (data?.detail) detail = String(data.detail);
        } catch {
          // ignore
        }
        setSubmitError(detail);
        return;
      }

      setSubmitted(true);
    } catch {
      setSubmitError(t.submit.failedTryAgain);
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!authChecked || !isAuthed) {
    return (
      <main className="min-h-screen bg-[#030014] flex items-center justify-center">
        <div className="text-white/80 text-sm">{isArabic ? "...جاري التحقق" : "Checking..."}</div>
      </main>
    );
  }

  return (
    <main className="relative min-h-screen bg-[#030014] overflow-x-hidden">
      <div className="fixed inset-0 -z-10 pointer-events-none bg-gradient-to-b from-black via-[#030014] to-[#0a0a1a]" />
      <div className="fixed inset-0 -z-10 pointer-events-none bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-blue-900/20 via-transparent to-transparent" />

      <div className="fixed inset-0 -z-10 pointer-events-none w-full h-full">
        <SparklesCore
          id="tsparticles-register"
          background="transparent"
          minSize={0.4}
          maxSize={1.2}
          particleDensity={60}
          className="w-full h-full"
          particleColor="#6366f1"
          speed={0.45}
        />
      </div>

      <nav className="relative z-50 px-2 sm:px-6 py-3 sm:py-4 border-b border-white/5">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2 select-none">
            <img src="/logo-04.png" alt="Talaria" className="h-8 w-8 sm:h-10 sm:w-10" />
            <span className="text-base sm:text-2xl font-bold text-white whitespace-nowrap">Talaria-Log</span>
          </Link>

          <Link 
            href="/bootcamp" 
            className="flex items-center gap-1.5 text-sm text-white/70 hover:text-white transition-colors px-3 py-1.5 rounded-full border border-white/10 hover:border-white/20 bg-white/5"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>{isArabic ? "رجوع" : "Back"}</span>
          </Link>
        </div>
      </nav>

      <section className="relative z-10 px-4 sm:px-6 py-10 sm:py-14">
        <div className="max-w-5xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="grid grid-cols-1 gap-6 sm:gap-10 items-start"
          >
            {!submitted ? (
              <div className="rounded-2xl bg-[#070b1b]/90 backdrop-blur-xl border border-white/10 p-5 sm:p-7">
                <div className="text-white text-2xl sm:text-3xl font-bold mb-2">{t.page.title}</div>
                <div className="text-neutral-300 mb-6">{t.page.intro}</div>

                <div className="rounded-xl border border-blue-500/20 bg-[#0b1026]/70 p-4 sm:p-5">
                  <div className="text-white font-semibold mb-3">
                    {t.page.rulesTitle}
                    <span className={`text-red-500 ${isArabic ? "mr-1" : "ml-1"}`}>*</span>
                  </div>
                  <div className="text-xs text-neutral-400 mb-3">{t.page.rulesChoiceHint}</div>

                <div className="max-h-[320px] overflow-y-auto pr-2">
                  {(() => {
                    const parsed = isArabic
                      ? parseArabicRules(t.page.rules)
                      : parseEnglishRules(t.page.rules);

                    return (
                      <div
                        dir={isArabic ? "rtl" : "ltr"}
                        className={
                          "space-y-5 text-sm text-neutral-300 leading-relaxed " +
                          (isArabic ? "text-right" : "text-left")
                        }
                      >
                        {isArabic && parsed.title ? (
                          <div className="text-white font-semibold text-base">{parsed.title}</div>
                        ) : null}
                        {parsed.intro ? <div className="text-neutral-300">{parsed.intro}</div> : null}

                        {parsed.sections.map((section) => (
                          <div key={section.title} className="space-y-3">
                            {section.title ? (
                              <div className="text-white font-semibold">{section.title}</div>
                            ) : null}

                            <ol className="space-y-3">
                              {section.items.map((item) => (
                                <li
                                  key={item.n + (item.label || "") + item.text}
                                  className="flex gap-3"
                                >
                                  {isArabic ? (
                                    <>
                                      <div className="shrink-0 w-10 text-white font-semibold tabular-nums text-right">
                                        <span dir="ltr">.{item.n}</span>
                                      </div>
                                      <div className="flex-1">
                                        <div>
                                          {item.label ? (
                                            <span className="text-white font-semibold">{item.label}: </span>
                                          ) : null}
                                          <span>{item.text}</span>
                                        </div>

                                        {item.sub && item.sub.length ? (
                                          <ul className="mt-2 space-y-1">
                                            {item.sub.map((s) => (
                                              <li key={s} className="flex gap-2 text-neutral-300">
                                                <span className="text-neutral-400">•</span>
                                                <span>{s}</span>
                                              </li>
                                            ))}
                                          </ul>
                                        ) : null}
                                      </div>
                                    </>
                                  ) : (
                                    <>
                                      <div className="shrink-0 w-8 text-white font-semibold tabular-nums text-left">
                                        {item.n}.
                                      </div>
                                      <div className="flex-1">
                                    <div>
                                      {item.label ? (
                                        <span className="text-white font-semibold">{item.label}: </span>
                                      ) : null}
                                      <span>{item.text}</span>
                                    </div>

                                    {item.sub && item.sub.length ? (
                                      <ul className="mt-2 space-y-1">
                                        {item.sub.map((s) => (
                                          <li
                                            key={s}
                                            className="flex gap-2 text-neutral-300"
                                          >
                                            <span className="text-neutral-400">-</span>
                                            <span>{s}</span>
                                          </li>
                                        ))}
                                      </ul>
                                    ) : null}
                                      </div>
                                    </>
                                  )}
                                </li>
                              ))}
                            </ol>
                          </div>
                        ))}
                      </div>
                    );
                  })()}
                </div>

                <div className="mt-4 text-xs text-neutral-400">{t.page.rulesNote}</div>

                <div className="mt-4 flex flex-col sm:flex-row gap-3">
                  <Button
                    type="button"
                    variant="ghost"
                    className={`border px-6 py-2 text-white transition-colors ${
                      rulesDecision === "agree"
                        ? "border-green-500/40 bg-green-500/15 text-green-100 hover:bg-green-500/15"
                        : "border-white/15 bg-transparent text-white/80 hover:bg-white/5"
                    }`}
                    onClick={() => {
                      setRulesDecision("agree");
                    }}
                  >
                    {t.page.rulesAgree}
                  </Button>
                  <Button
                    type="button"
                    variant="ghost"
                    className={`border px-6 py-2 transition-colors ${
                      rulesDecision === "disagree"
                        ? "border-red-500/40 bg-red-500/15 text-red-100 hover:bg-red-500/15"
                        : "border-white/15 bg-transparent text-white/80 hover:bg-white/5"
                    }`}
                    onClick={() => {
                      setRulesDecision("disagree");
                    }}
                  >
                    {t.page.rulesDisagree}
                  </Button>
                </div>

                {rulesDecision === "agree" ? (
                  <div className="mt-3 text-xs text-green-300">{t.page.rulesAgreeNote}</div>
                ) : null}
                {rulesDecision === "disagree" ? (
                  <div className="mt-3 text-xs text-red-300">{t.page.rulesDisagreeNote}</div>
                ) : null}
                {errors.rulesDecision ? (
                  <div className="mt-3 text-xs text-red-400">{errors.rulesDecision}</div>
                ) : null}
              </div>

                <div className="mt-6 grid gap-3">
                  <div className="text-sm text-neutral-300">
                    {t.page.legal}
                    <span className={isArabic ? "mr-2" : "ml-2"}>
                      <Link href="/terms" className="text-blue-400 hover:text-blue-300">{t.page.terms}</Link>
                      <span className="mx-2 text-white/30">|</span>
                      <Link href="/privacy" className="text-blue-400 hover:text-blue-300">{t.page.privacy}</Link>
                      <span className="mx-2 text-white/30">|</span>
                      <Link href="/disclaimer" className="text-blue-400 hover:text-blue-300">{t.page.disclaimer}</Link>
                    </span>
                  </div>
                </div>
              </div>
            ) : null}

            <div className="rounded-2xl bg-[#070b1b]/90 backdrop-blur-xl border border-white/10 p-5 sm:p-7 relative">
              {isSubmitting ? (
                <div className="absolute inset-0 z-20 rounded-2xl bg-black/40 backdrop-blur-sm flex items-center justify-center">
                  <div className="flex items-center gap-3 text-white">
                    <span className="h-5 w-5 rounded-full border-2 border-white/30 border-t-white animate-spin" />
                    <span className="text-sm font-medium">{t.form.saving}</span>
                  </div>
                </div>
              ) : null}

              {!submitted ? (
                rulesDecision === "agree" ? (
                  <form onSubmit={onSubmit} className="grid gap-4">
                    {submitError ? (
                      <div className="rounded-xl border border-red-500/20 bg-red-500/10 p-3 text-red-200 text-sm">
                        {submitError}
                      </div>
                    ) : null}
                    <div>
                      <label className="block text-sm font-medium text-white mb-1">
                        {t.form.fullName}
                        <span className={`text-red-500 ${isArabic ? "mr-1" : "ml-1"}`}>*</span>
                      </label>
                      <input
                        className={`w-full rounded-lg border border-white/10 bg-[#050815] px-3 py-2 text-white placeholder:text-neutral-500 focus:outline-none focus:ring-2 focus:ring-blue-500/60 ${
                          isAuthed ? "opacity-80 cursor-not-allowed" : ""
                        }`}
                        value={fullName}
                        readOnly={isAuthed}
                        onChange={isAuthed ? undefined : (e) => setFullName(e.target.value)}
                        placeholder={t.form.fullNamePh}
                        required
                      />
                      {errors.fullName && <div className="mt-1 text-xs text-red-400">{errors.fullName}</div>}
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-white mb-1">
                        {t.form.email}
                        <span className={`text-red-500 ${isArabic ? "mr-1" : "ml-1"}`}>*</span>
                      </label>
                      <input
                        className={`w-full rounded-lg border border-white/10 bg-[#050815] px-3 py-2 text-white placeholder:text-neutral-500 focus:outline-none focus:ring-2 focus:ring-blue-500/60 ${
                          isAuthed ? "opacity-80 cursor-not-allowed" : ""
                        }`}
                        value={email}
                        readOnly={isAuthed}
                        onChange={isAuthed ? undefined : (e) => setEmail(e.target.value)}
                        placeholder={t.form.emailPh}
                        inputMode="email"
                        required
                      />
                      {errors.email && <div className="mt-1 text-xs text-red-400">{errors.email}</div>}
                    </div>

                  <div>
                    <label className="block text-sm font-medium text-white mb-1">
                      {t.form.country}
                      <span className={`text-red-500 ${isArabic ? "mr-1" : "ml-1"}`}>*</span>
                    </label>
                    <div ref={countryDropdownRef} className="relative">
                      <input
                        dir={isArabic ? "rtl" : "ltr"}
                        className={`w-full rounded-lg border border-white/10 bg-[#050815] px-3 py-2 text-white placeholder:text-neutral-500 focus:outline-none focus:ring-2 focus:ring-blue-500/60 ${
                          isArabic ? "text-right" : ""
                        }`}
                        value={countryQuery}
                        onFocus={() => setCountryDropdownOpen(true)}
                        onChange={(e) => {
                          const next = e.target.value;
                          setCountryQuery(next);
                          setCountryDropdownOpen(true);

                          if (country && next.trim() !== country) {
                            setCountry("");
                            setPhone("");
                          }
                        }}
                        onKeyDown={(e) => {
                          if (e.key === "Enter") {
                            const first = filteredArabCountries[0] || filteredOtherCountries[0];
                            if (first) {
                              e.preventDefault();
                              onCountryChange(first.name);
                            }
                          }
                          if (e.key === "Escape") {
                            setCountryDropdownOpen(false);
                          }
                        }}
                        placeholder={t.form.countrySearchPh}
                        required
                      />

                      {countryDropdownOpen ? (
                        <div className="absolute z-30 mt-2 w-full rounded-xl border border-white/10 bg-[#050815] shadow-lg overflow-hidden">
                          <div className="max-h-64 overflow-y-auto">
                            {filteredArabCountries.length ? (
                              <div className="px-3 pt-3 pb-2 text-xs font-semibold text-neutral-400">
                                {t.form.arabicCountries}
                              </div>
                            ) : null}
                            {filteredArabCountries.map((c) => (
                              <button
                                key={c.name}
                                type="button"
                                className={`w-full px-3 py-2 text-sm text-white hover:bg-white/5 text-left ${
                                  isArabic ? "text-right" : ""
                                }`}
                                onClick={() => onCountryChange(c.name)}
                              >
                                {c.name}
                              </button>
                            ))}

                            {filteredOtherCountries.length ? (
                              <div className="px-3 pt-3 pb-2 text-xs font-semibold text-neutral-400">
                                {t.form.allCountries}
                              </div>
                            ) : null}
                            {filteredOtherCountries.map((c) => (
                              <button
                                key={c.name}
                                type="button"
                                className={`w-full px-3 py-2 text-sm text-white hover:bg-white/5 text-left ${
                                  isArabic ? "text-right" : ""
                                }`}
                                onClick={() => onCountryChange(c.name)}
                              >
                                {c.name}
                              </button>
                            ))}

                            {!filteredArabCountries.length && !filteredOtherCountries.length ? (
                              <div className="px-3 py-3 text-sm text-neutral-400">
                                {t.form.countrySelect}
                              </div>
                            ) : null}
                          </div>
                        </div>
                      ) : null}
                    </div>
                    {errors.country && <div className="mt-1 text-xs text-red-400">{errors.country}</div>}
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-white mb-1">{t.form.phone}</label>
                    <input
                      dir="ltr"
                      className="w-full rounded-lg border border-white/10 bg-[#050815] px-3 py-2 text-white text-left placeholder:text-neutral-500 focus:outline-none focus:ring-2 focus:ring-blue-500/60 disabled:opacity-60"
                      value={phone}
                      onChange={(e) => setPhone(ensureDialPrefix(e.target.value, selectedDial))}
                      onKeyDown={(e) => {
                        if (!selectedDial) return;
                        const prefix = `${selectedDial} `;
                        const el = e.currentTarget;
                        const start = el.selectionStart ?? 0;
                        const end = el.selectionEnd ?? 0;

                        if (e.key === "Backspace" && start === end && start <= prefix.length) {
                          e.preventDefault();
                        }
                        if (e.key === "Delete" && start < prefix.length) {
                          e.preventDefault();
                        }
                      }}
                      onFocus={(e) => {
                        if (!selectedDial) return;
                        const prefix = `${selectedDial} `;
                        if (!e.currentTarget.value.startsWith(prefix)) {
                          setPhone((prev) => ensureDialPrefix(prev, selectedDial));
                        }
                      }}
                      placeholder={selectedDial ? `${selectedDial} 555 123 4567` : t.form.phoneSelectFirst}
                      inputMode="tel"
                      disabled={!country}
                    />
                    {errors.phone && <div className="mt-1 text-xs text-red-400">{errors.phone}</div>}
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-white mb-1">
                      {t.form.age}
                      <span className={`text-red-500 ${isArabic ? "mr-1" : "ml-1"}`}>*</span>
                    </label>
                    <input
                      className="w-full rounded-lg border border-white/10 bg-[#050815] px-3 py-2 text-white placeholder:text-neutral-500 focus:outline-none focus:ring-2 focus:ring-blue-500/60"
                      value={age}
                      onChange={(e) => setAge(e.target.value)}
                      placeholder={t.form.agePh}
                      inputMode="numeric"
                      required
                    />
                    {errors.age && <div className="mt-1 text-xs text-red-400">{errors.age}</div>}
                    {ageRejected ? (
                      <div className="mt-3 rounded-xl border border-red-500/25 bg-red-500/10 p-4">
                        <div className="text-red-200 font-semibold text-sm mb-2">
                          {t.validation.ageUnder18Title}
                        </div>
                        <div className="text-red-100/90 text-xs leading-relaxed">
                          {t.validation.ageUnder18Text}
                        </div>
                      </div>
                    ) : null}
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-white mb-1">{t.form.telegram}</label>
                    <input
                      className="w-full rounded-lg border border-white/10 bg-[#050815] px-3 py-2 text-white placeholder:text-neutral-500 focus:outline-none focus:ring-2 focus:ring-blue-500/60"
                      value={telegram}
                      onChange={(e) => setTelegram(e.target.value)}
                      placeholder={t.form.telegramPh}
                    />
                    {errors.telegram && <div className="mt-1 text-xs text-red-400">{errors.telegram}</div>}
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-white mb-1">
                      {t.form.discord}
                      <span className={`text-red-500 ${isArabic ? "mr-1" : "ml-1"}`}>*</span>
                    </label>
                    <input
                      className="w-full rounded-lg border border-white/10 bg-[#050815] px-3 py-2 text-white placeholder:text-neutral-500 focus:outline-none focus:ring-2 focus:ring-blue-500/60"
                      value={discord}
                      onChange={(e) => setDiscord(e.target.value)}
                      placeholder={t.form.discordPh}
                      required
                    />
                    {errors.discord && <div className="mt-1 text-xs text-red-400">{errors.discord}</div>}
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-white mb-1">{t.form.instagram}</label>
                    <input
                      className="w-full rounded-lg border border-white/10 bg-[#050815] px-3 py-2 text-white placeholder:text-neutral-500 focus:outline-none focus:ring-2 focus:ring-blue-500/60"
                      value={instagram}
                      onChange={(e) => setInstagram(e.target.value)}
                      placeholder={t.form.instagramPh}
                    />
                    {errors.instagram && <div className="mt-1 text-xs text-red-400">{errors.instagram}</div>}
                  </div>

                  <div className="grid gap-2">
                    <label className="flex items-start gap-3 text-sm text-neutral-200">
                      <input
                        type="checkbox"
                        className="mt-1 h-4 w-4 rounded border-white/20 bg-[#050815]"
                        checked={agreeTerms}
                        onChange={(e) => setAgreeTerms(e.target.checked)}
                      />
                      <span>
                        {t.form.agreeTermsA}
                        <Link href="/terms" className="text-blue-400 hover:text-blue-300">{t.form.agreeTermsB}</Link>
                        {t.form.agreeTermsC}
                        <Link href="/privacy" className="text-blue-400 hover:text-blue-300">{t.form.agreeTermsD}</Link>.
                        <span className={`text-red-500 ${isArabic ? "mr-1" : "ml-1"}`}>*</span>
                      </span>
                    </label>
                    {errors.agreeTerms && <div className="text-xs text-red-400">{errors.agreeTerms}</div>}
                  </div>

                  <div className="pt-2 flex items-center gap-3">
                    <Button
                      disabled={isSubmitting || rulesDecision !== "agree"}
                      className="bg-blue-600 hover:bg-blue-700 text-white px-6"
                    >
                      {isSubmitting ? (
                        <span className="inline-flex items-center gap-2">
                          <span className="h-4 w-4 rounded-full border-2 border-white/30 border-t-white animate-spin" />
                          {t.form.submitting}
                        </span>
                      ) : (
                        t.form.submit
                      )}
                    </Button>
                    <Link href="/bootcamp">
                      <Button
                        type="button"
                        variant="ghost"
                        className="text-white hover:text-blue-400 px-2"
                        aria-label={t.form.backToBootcamp}
                      >
                        <ArrowLeft className="w-5 h-5" />
                      </Button>
                    </Link>
                  </div>

                  <div className="text-xs text-neutral-500">
                    {t.form.note}
                  </div>
                  </form>
                ) : (
                  <div className="rounded-xl border border-white/10 bg-white/5 p-4 text-white/80 text-sm">
                    {rulesDecision === "disagree" ? t.page.rulesDisagreeNote : t.page.rulesGatePrompt}
                  </div>
                )
              ) : (
                <div className="text-center py-6">
                  <div className="text-white text-2xl font-bold mb-2">{t.success.title}</div>
                  <div className="text-neutral-300 mb-6">
                    {t.success.thanksA}
                    {fullName.trim()}
                    {t.success.thanksB}
                    <span className="text-white">{email.trim()}</span>.
                  </div>

                  <div className="rounded-xl border border-green-500/20 bg-green-500/10 p-4 text-green-200 text-sm mb-6">
                    {t.success.checkEmail}
                  </div>
                </div>
              )}
            </div>
          </motion.div>
        </div>
      </section>

      <SiteDisclosuresFooter />
    </main>
  );
}
