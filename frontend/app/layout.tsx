import "./globals.css";

export const metadata = {
  title: "MetricMind",
  description: "Agentic Semantic BI Engine",
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