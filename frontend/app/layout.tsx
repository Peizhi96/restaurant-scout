import type { Metadata } from "next";

import { Sidebar } from "@/components/sidebar";
import "./globals.css";

export const metadata: Metadata = {
  title: { default: "Restaurant Scout", template: "%s · Restaurant Scout" },
  description: "Bay Area restaurant acquisition and catering intelligence dashboard.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <div className="app-shell"><Sidebar /><main className="main-content">{children}</main></div>
      </body>
    </html>
  );
}
