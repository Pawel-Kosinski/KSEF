"use client";

import { useEffect, useState, type ComponentType } from "react";
import type { LucideProps } from "lucide-react";

type HydrationSafeIconProps = LucideProps & {
  icon: ComponentType<LucideProps>;
};

/**
 * Ikony Lucide renderowane po mount — omija hydration mismatch
 * od rozszerzeń (np. Dark Reader) modyfikujących atrybuty SVG.
 */
export function HydrationSafeIcon({
  icon: Icon,
  className,
  ...props
}: HydrationSafeIconProps) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return <span className={className} aria-hidden="true" />;
  }

  return <Icon className={className} {...props} />;
}
