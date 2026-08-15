import type { Metadata } from "next";
import "./globals.scss";

export const metadata: Metadata = {
  title: "Movie Lists",
  description: "Browse curated movie lists from TMDB",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
