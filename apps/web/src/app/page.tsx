import { redirect } from "next/navigation";

/** Root URL opens the login page first. */
export default function HomePage() {
  redirect("/login");
}
