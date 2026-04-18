import { Topbar } from "@/components/dashboard/topbar";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-d8x-background text-d8x-text-primary flex flex-col">
      <Topbar />
      <main className="flex-1">{children}</main>
    </div>
  );
}
