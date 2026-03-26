import type { Metadata } from "next";
import { Rajdhani, Space_Mono } from "next/font/google";
import "./globals.css";
import { Providers } from "@/components/Providers";

const rajdhani = Rajdhani({
  variable: "--font-rajdhani",
  weight: ["400", "500", "600", "700"],
  subsets: ["latin"],
});

const spaceMono = Space_Mono({
  variable: "--font-space-mono",
  weight: ["400", "700"],
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "GeoScope - Live Geopolitical Map",
  description: "Interactive world map tracking live geopolitical events, conflicts, and global politics",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body
        className={`${rajdhani.variable} ${spaceMono.variable} bg-[#081116] text-[#eef3ef] antialiased`}
      >
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
