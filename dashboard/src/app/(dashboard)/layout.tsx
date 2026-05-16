import { Topbar } from "@/components/dashboard/topbar";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-ink-950 text-ink-50 flex flex-col">
      <Topbar />
      <main className="flex-1">{children}</main>
    </div>
  );
}
