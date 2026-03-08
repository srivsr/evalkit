import { Sidebar } from "@/components/dashboard/Sidebar";
import { Footer } from "@/components/Footer";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-screen bg-slate-950">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-y-auto">
        <main className="flex-1">{children}</main>
        <Footer />
      </div>
    </div>
  );
}
