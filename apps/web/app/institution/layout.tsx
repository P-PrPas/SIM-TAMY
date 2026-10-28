import type { ReactNode } from "react";

import { InstitutionShell } from "@/components/institution-shell";

export default function InstitutionLayout({ children }: { children: ReactNode }) {
  return <InstitutionShell>{children}</InstitutionShell>;
}
