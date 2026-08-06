import { Suspense } from "react";

export default function InvoiceDetailLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <Suspense fallback={null}>{children}</Suspense>;
}
