export default function CarePlanCard({ carePlan }) {
  return (
    <div className="mt-3 rounded border bg-slate-50 p-3">
      <p className="text-sm text-slate-700"><strong>Diagnosis:</strong> {carePlan.diagnosis}</p>
      <p className="mt-1 text-sm text-slate-700"><strong>Recommendation:</strong> {carePlan.recommendation}</p>
    </div>
  );
}
