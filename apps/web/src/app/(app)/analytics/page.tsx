import { redirect } from "next/navigation";

/** Analytics is merged into Dashboard — keep old URLs working. */
export default function AnalyticsPage() {
  redirect("/dashboard");
}
