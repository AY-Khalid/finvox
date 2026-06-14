import "./globals.css";

export const metadata = {
  title: "Finvox | Talk your sales. We keep the books.",
  description:
    "Voice-first AI bookkeeping for Nigerian traders. Send a WhatsApp voice note, get a proper ledger and a credit-ready financial identity.",
  manifest: "/manifest.json",
  appleWebApp: { capable: true, statusBarStyle: "default", title: "Finvox" },
};

export const viewport = {
  themeColor: "#0BA859",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>
        {children}
        <script
          dangerouslySetInnerHTML={{
            __html: `if ('serviceWorker' in navigator) {
              window.addEventListener('load', () => navigator.serviceWorker.register('/sw.js').catch(()=>{}));
            }`,
          }}
        />
      </body>
    </html>
  );
}
