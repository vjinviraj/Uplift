import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Uplift — AI Commerce Console",
  description: "Agentic commerce for gaming merchants",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body>{children}</body>
    </html>
  );
}