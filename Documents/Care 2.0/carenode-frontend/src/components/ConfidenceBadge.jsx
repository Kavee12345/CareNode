export default function ConfidenceBadge({ value }) {
  const level = value >= 0.85 ? 'bg-emerald-500 text-white' : 'bg-rose-500 text-white';
  return (
    <span className={`rounded-full px-3 py-1 text-xs font-semibold ${level}`}>
      {Number(value).toLocaleString(undefined, { style: 'percent', minimumFractionDigits: 0 })}
    </span>
  );
}
