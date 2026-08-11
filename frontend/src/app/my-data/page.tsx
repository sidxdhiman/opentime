import { redirect } from "next/navigation";

export default function MyDataRedirect() {
  redirect("/me");
}