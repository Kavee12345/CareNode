import { useState } from 'react';
import FileUploader from '../../components/FileUploader';
import { submitIntake } from '../../services/api';

export default function IntakePage() {
  const [symptoms, setSymptoms] = useState('');
  const [currentMeds, setCurrentMeds] = useState('');
  const [labFile, setLabFile] = useState(null);
  const [status, setStatus] = useState('');

  const handleSubmit = async (event) => {
    event.preventDefault();
    setStatus('Submitting...');

    const medsList = currentMeds
      .split(',')
      .map((med) => med.trim())
      .filter(Boolean);

    try {
      const data = new FormData();
      data.append('symptoms', symptoms);
      data.append('currentMeds', JSON.stringify(medsList));
      if (labFile) data.append('labReport', labFile);

      const response = await submitIntake(data);
      if (response?.data?.success) {
        setStatus('Intake submitted successfully.');
      } else {
        setStatus('Unexpected API response.');
      }
    } catch (error) {
      console.error(error);

      const maybeMessage =
        error?.response?.data?.message ||
        error?.response?.data?.error ||
        error?.message ||
        'Error submitting intake.';

      setStatus(`Error submitting intake: ${maybeMessage}`);
    }
  };

  return (
    <div className="rounded-xl bg-white p-6 shadow-lg">
      <h2 className="text-xl font-bold">Patient Intake</h2>
      <form onSubmit={handleSubmit} className="mt-4 space-y-4">
        <textarea
          className="w-full rounded border p-3"
          placeholder="Symptoms (comma-separated or free text)"
          value={symptoms}
          onChange={(e) => setSymptoms(e.target.value)}
          required
          rows={4}
        />
        <input
          className="w-full rounded border p-2"
          placeholder="Current medications (comma-separated)"
          value={currentMeds}
          onChange={(e) => setCurrentMeds(e.target.value)}
        />

        <div className="text-sm text-slate-500">
          Uploading a lab report uses backend Vision AI. If the backend key is invalid,
          leave this empty and submit symptoms + medications only.
        </div>

        <FileUploader onFileSelect={setLabFile} />

        <button
          className="rounded bg-blue-600 px-4 py-2 text-white hover:bg-blue-700"
          type="submit"
        >
          Submit Intake
        </button>
      </form>
      {status && <p className="mt-3 text-sm text-slate-700">{status}</p>}
    </div>
  );
}
