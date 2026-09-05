import type { Metadata } from "next";
import { Geist_Mono, Manrope, Space_Grotesk } from "next/font/google";
import "./globals.css";

const manrope = Manrope({
  variable: "--font-manrope",
  subsets: ["latin"],
});

const spaceGrotesk = Space_Grotesk({
  variable: "--font-space-grotesk",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Modelia — CASE tool UML multi-organización",
  description:
    "Modelia es el CASE tool donde tus equipos modelan, colaboran y generan código a partir de un único modelo UML canónico, organizados en cuentas multi-tenant.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="es"
      className={`${manrope.variable} ${spaceGrotesk.variable} ${geistMono.variable}`}
    >
      <body>{children}</body>
    </html>
  );
}
