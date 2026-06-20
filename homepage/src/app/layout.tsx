import type { Metadata } from "next";
import localFont from "next/font/local";
import Script from "next/script";
import "./globals.css";
import { LanguageProvider } from "./LanguageProvider";
import CookieConsent from "./CookieConsent";

const zain = localFont({
  variable: "--font-zain",
  src: [
    { path: "../../font/Zain/Zain-ExtraLight.ttf", weight: "200", style: "normal" },
    { path: "../../font/Zain/Zain-Light.ttf", weight: "300", style: "normal" },
    { path: "../../font/Zain/Zain-Regular.ttf", weight: "400", style: "normal" },
    { path: "../../font/Zain/Zain-Bold.ttf", weight: "700", style: "normal" },
    { path: "../../font/Zain/Zain-ExtraBold.ttf", weight: "800", style: "normal" },
    { path: "../../font/Zain/Zain-Black.ttf", weight: "900", style: "normal" },
    { path: "../../font/Zain/Zain-Italic.ttf", weight: "400", style: "italic" },
    { path: "../../font/Zain/Zain-LightItalic.ttf", weight: "300", style: "italic" },
  ],
});

export const metadata: Metadata = {
  title: "Talaria - Professional Trading Platform",
  description: "Advanced charting and backtesting platform for professional traders",
  other: {
    "impact-site-verification": "1d03ebf8-2524-48bf-970a-fdebe0f8a5fc",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ar" dir="rtl" className="dark" suppressHydrationWarning>
      <head>
        <Script
          src="https://www.googletagmanager.com/gtag/js?id=G-2S8BJ30FJE"
          strategy="afterInteractive"
        />
        <Script id="google-analytics" strategy="afterInteractive">
          {`
            window.dataLayer = window.dataLayer || [];
            function gtag(){dataLayer.push(arguments);}
            gtag('js', new Date());
            gtag('config', 'G-2S8BJ30FJE');
          `}
        </Script>
      </head>
      <body className={`${zain.variable} font-sans antialiased`}>
        <LanguageProvider>
          {children}
          <CookieConsent />
        </LanguageProvider>
      </body>
    </html>
  );
}
