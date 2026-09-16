import type { Metadata } from "next";
import { Geist, Old_Standard_TT } from "next/font/google";
import "./globals.css";
import { cn } from "@/lib/utils";

const geist = Geist({ subsets: ["latin"], variable: "--font-sans" });
const oldStandard = Old_Standard_TT({
  subsets: ["latin"],
  weight: ["400", "700"],
  variable: "--font-serif",
});

const siteUrl =
  process.env.VERCEL_PROJECT_PRODUCTION_URL != null
    ? `https://${process.env.VERCEL_PROJECT_PRODUCTION_URL}`
    : process.env.VERCEL_URL != null
      ? `https://${process.env.VERCEL_URL}`
      : "http://localhost:3000";

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: "Gazette. Your morning paper, as a picture.",
  description:
    "A Hermes agent that writes your morning newspaper overnight and texts you the front page as a photo.",
  openGraph: {
    title: "Gazette",
    description: "Your morning paper, as a picture.",
    images: [{ url: "/editions/planet.png" }],
  },
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={cn("h-full font-sans", geist.variable, oldStandard.variable)}
    >
      <body className="min-h-full bg-background text-foreground antialiased">
        {children}
      </body>
    </html>
  );
}
