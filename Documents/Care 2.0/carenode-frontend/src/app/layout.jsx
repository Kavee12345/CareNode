import { Link, Outlet } from 'react-router-dom';
import '../styles/globals.css';

export default function Layout() {
  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <header className="border-b bg-white shadow-sm">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3 sm:px-6">
          <h1 className="text-lg font-bold">CareNode 2.0</h1>
          <nav className="space-x-2">
            <Link className="rounded-md px-3 py-1 text-sm font-medium text-slate-700 hover:bg-slate-100" to="/">Home</Link>
            <Link className="rounded-md px-3 py-1 text-sm font-medium text-slate-700 hover:bg-slate-100" to="/intake">Intake</Link>
            <Link className="rounded-md px-3 py-1 text-sm font-medium text-slate-700 hover:bg-slate-100" to="/dashboard">Dashboard</Link>
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-6xl p-4 sm:p-6">
        <Outlet />
      </main>
    </div>
  );
}
