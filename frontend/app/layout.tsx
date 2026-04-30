import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Austin RHUG OpenShift AI Chat",
  description: "Next.js frontend for the Austin RHUG sample inference backend",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
