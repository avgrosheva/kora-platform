import type { Metadata } from "next";
import { Providers } from "./providers";
import "./globals.css";
import "../styles/kora.css";
import { cn } from "@/lib/utils";

export const metadata: Metadata = {
  title: "Kora — Revenue Intelligence Platform",
  description: "AI-powered investment analysis and due diligence.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={cn("dark", "font-sans")}>
      <body className="min-h-screen bg-background font-sans antialiased">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}