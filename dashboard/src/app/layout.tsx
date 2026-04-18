import type { Metadata } from "next";
import { Providers } from "@/lib/providers";
import "./globals.css";

export const metadata: Metadata = {
  title: "D8X — Eight AI Agents. One Complete SDLC.",
  description:
    "D8X automates the full software development lifecycle with 8 specialized AI agents: Ingest, Discover, Design, Prototype, Plan, Build, Test, Ship.",
  keywords: ["AI", "SDLC", "software development", "automation", "legacy modernization"],
  openGraph: {
    title: "D8X — Eight AI Agents. One Complete SDLC.",
    description: "The AI-powered platform that takes your project from requirements to production.",
    type: "website",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
