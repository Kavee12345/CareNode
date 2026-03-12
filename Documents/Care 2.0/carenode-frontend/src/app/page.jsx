export default function HomePage() {
  return (
    <div className="rounded-xl bg-white p-6 shadow-lg">
      <h2 className="text-2xl font-bold">Welcome to CareNode 2.0</h2>
      <p className="mt-2 text-slate-600">
        Rapid patient intake with vision lab report parsing, medication interaction checks, and AI-guided care planning.
      </p>
      <div className="mt-4 grid gap-4 sm:grid-cols-2">
        <div className="rounded-lg border p-4">Form-based intake workflow</div>
        <div className="rounded-lg border p-4">Clinical escalation dashboard</div>
      </div>
    </div>
  );
}
