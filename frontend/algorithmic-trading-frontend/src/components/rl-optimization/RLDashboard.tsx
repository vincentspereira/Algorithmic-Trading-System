// frontend/algorithmic-trading-frontend/src/components/rl-optimization/RLDashboard.tsx

import React, { useState } from 'react';
import TrainingMonitor from './TrainingMonitor';
import ModelSelector from './ModelSelector';
import PerformanceChart from './PerformanceChart';

const RLDashboard: React.FC = () => {
    const [selectedModel, setSelectedModel] = useState<string | null>(null);
    const [trainingJobId, setTrainingJobId] = useState<string | null>(null);

    const handleStartTraining = async () => {
        // Mock API call to start training
        const response = await fetch('/api/rl/train', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                agent_name: 'PPO',
                instrument_id: 'BTC/USD',
                start_date: '2023-01-01',
                end_date: '2024-01-01',
            }),
        });
        const data = await response.json();
        setTrainingJobId(data.job_id);
    };

    return (
        <div className="p-4 bg-gray-900 text-white min-h-screen">
            <h1 className="text-3xl font-bold mb-4">RL Strategy Optimization</h1>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                <div className="bg-gray-800 p-4 rounded-lg">
                    <h2 className="text-xl font-semibold mb-2">Controls</h2>
                    <button
                        onClick={handleStartTraining}
                        className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded"
                    >
                        Start New Training Job
                    </button>
                </div>
                
                <div className="bg-gray-800 p-4 rounded-lg">
                    <ModelSelector onSelectModel={setSelectedModel} />
                </div>
            </div>

            {trainingJobId && (
                <div className="bg-gray-800 p-4 rounded-lg mb-4">
                    <TrainingMonitor jobId={trainingJobId} />
                </div>
            )}

            <div className="bg-gray-800 p-4 rounded-lg">
                <h2 className="text-xl font-semibold mb-2">Performance</h2>
                {selectedModel ? (
                    <PerformanceChart modelId={selectedModel} />
                ) : (
                    <p>Select a model to view its performance.</p>
                )}
            </div>
        </div>
    );
};

export default RLDashboard;