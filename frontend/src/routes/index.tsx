import { createFileRoute, redirect } from "@tanstack/react-router";

export const Route = createFileRoute("/")({
  beforeLoad: () => {
    if (typeof window === "undefined") return;
    const raw = localStorage.getItem("thinkbook.auth");
    if (raw) throw redirect({ to: "/notebooks" });
    throw redirect({ to: "/login" });
  },
  component: () => null,
  ssr: false,
});
