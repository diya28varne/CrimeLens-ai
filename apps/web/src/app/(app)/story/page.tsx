import { redirect } from "next/navigation";

/** Story lives under Explain — keep old /story URLs working. */
export default function StoryPage() {
  redirect("/explain?view=story");
}
