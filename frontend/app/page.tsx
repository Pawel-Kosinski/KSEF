import { Suspense } from "react";

import { DashboardView } from "@/components/DashboardView";

export default function DashboardPage() {
  return (
    <Suspense fallback={null}>
      <DashboardView />
    </Suspense>
  );
}
