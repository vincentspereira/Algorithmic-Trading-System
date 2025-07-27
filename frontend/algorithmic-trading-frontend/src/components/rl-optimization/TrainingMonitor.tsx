// frontend/algorithmic-trading-frontend/src/components/rl-optimization/TrainingMonitor.tsx

import React, { useState, useEffect } from 'react';

interface TrainingMonitorProps {
    jobId: string;
}

const TrainingMonitor: React.FC<TrainingMonitorProps> = ({ jobId }) => {
    const [status, setStatus] = useState<string | null>(null);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const interval = setInterval(async () => {
            try {
                const response = await fetch(`/api/rl/training/${jobId}`);
                if (response.ok) {
                    const data = await response.json();
                    setStatus(data.status.status);
                    if (data.status.status === 'completed' || data.status.status === 'failed') {
                        clearInterval(interval);
                    }
                    if (data.status.error) {
                        setError(data.status.error);
                    }
                } else {
                    setStatus('error');
                    clearInterval(interval);
                }
            } catch (err) {
                setStatus('error');
                setError('Failed to fetch training status.');
                clearInterval(interval);
            }
        }, 5000); // Poll every 5 seconds

        return () => clearInterval(interval);
    }, [jobId]);

    return (
        <div>
            <h3 className="text-lg font-semibold">Training Job: {jobId}</h3>
            {status ? (
                <p>Status: <span className={`font-bold ${status === 'completed' ? 'text-green-500' : 'text-yellow-500'}`}>{status}</span></p>
            ) : (
                <p>Loading status...</p>
            )}
            {error && <p className="text-red-500">Error: {error}</p>}
        </div>
    );
};

export default TrainingMonitor;