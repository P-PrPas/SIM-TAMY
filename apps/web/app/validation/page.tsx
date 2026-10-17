import { ValidationDashboard } from "@/components/validation-dashboard";
import results from "@/public/validation-results.json";

export default function ValidationPage() {
  return <ValidationDashboard report={results} />;
}
