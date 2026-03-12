import ConfidenceBadge from '../../components/ConfidenceBadge';
import CarePlanCard from '../../components/CarePlanCard';

const mockCases = [
  {
    id: '1',
    patient: 'Max Walker',
    confidence: 0.92,
    plan: {
      diagnosis: 'Type II Diabetes Alert',
      recommendation: 'Immediate endocrinology consult and lab retest',
    },
  },
  {
    id: '2',
    patient: 'Amelia Rees',
    confidence: 0.76,
    plan: {
      diagnosis: 'Possible drug-drug interaction',
      recommendation: 'Hold one medication and confirm with pharm',
    },
  },
];

export default function DashboardPage() {
  return (
    <div className="space-y-4">
      <h2 className="text-xl font-bold">Escalated Cases</h2>
      {mockCases.map((c) => (
        <div key={c.id} className="rounded-lg border bg-white p-4 shadow-sm">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold">{c.patient}</h3>
            <ConfidenceBadge value={c.confidence} />
          </div>
          <CarePlanCard carePlan={c.plan} />
        </div>
      ))}
    </div>
  );
}
