import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'AuroraTime — Explore the past. Predict the night.',
  description: 'Explore historical aurora-viewing conditions, compare model configurations, and predict the night transparently.',
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
