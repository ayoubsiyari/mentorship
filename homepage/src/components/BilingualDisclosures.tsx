import React from "react";

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

export function BilingualDisclosures({
  en,
  ar,
  className,
  englishOnly,
}: {
  en: Disclosures;
  ar: Disclosures;
  className?: string;
  /** When true, only the English column is shown (e.g. English-only pages). */
  englishOnly?: boolean;
}) {
  const bodyClass =
    "space-y-8 text-sm leading-relaxed " +
    (className ? className : "text-neutral-400");

  if (englishOnly) {
    return (
      <div className={bodyClass} dir="ltr">
        <div className="space-y-8 text-left">
          <div>
            <div className="text-white font-semibold mb-2">{en.riskTitle}</div>
            <p>{en.riskText}</p>
          </div>

          <div>
            <div className="text-white font-semibold mb-2">{en.hypoTitle}</div>
            <p>{en.hypoText}</p>
          </div>

          <div>
            <div className="text-white font-semibold mb-2">{en.liveTitle}</div>
            <p>{en.liveText}</p>
          </div>

          <div>
            <div className="text-white font-semibold mb-2">{en.testTitle}</div>
            <p>{en.testText}</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={bodyClass}>
      <div dir="ltr" className="space-y-8 text-left">
        <div>
          <div className="text-white font-semibold mb-2">{en.riskTitle}</div>
          <p>{en.riskText}</p>
        </div>

        <div>
          <div className="text-white font-semibold mb-2">{en.hypoTitle}</div>
          <p>{en.hypoText}</p>
        </div>

        <div>
          <div className="text-white font-semibold mb-2">{en.liveTitle}</div>
          <p>{en.liveText}</p>
        </div>

        <div>
          <div className="text-white font-semibold mb-2">{en.testTitle}</div>
          <p>{en.testText}</p>
        </div>
      </div>

      <div className="h-px bg-white/10" />

      <div dir="rtl" className="space-y-8 text-right">
        <div>
          <div className="text-white font-semibold mb-2">{ar.riskTitle}</div>
          <p>{ar.riskText}</p>
        </div>

        <div>
          <div className="text-white font-semibold mb-2">{ar.hypoTitle}</div>
          <p>{ar.hypoText}</p>
        </div>

        <div>
          <div className="text-white font-semibold mb-2">{ar.liveTitle}</div>
          <p>{ar.liveText}</p>
        </div>

        <div>
          <div className="text-white font-semibold mb-2">{ar.testTitle}</div>
          <p>{ar.testText}</p>
        </div>
      </div>
    </div>
  );
}
