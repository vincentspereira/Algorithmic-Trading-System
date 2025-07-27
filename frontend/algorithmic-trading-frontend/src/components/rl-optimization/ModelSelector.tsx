// frontend/algorithmic-trading-frontend/src/components/rl-optimization/ModelSelector.tsx

import React, { useState, useEffect } from 'react';

interface ModelSelectorProps {
    onSelectModel: (modelId: string) => void;
}

interface Model {
    id: string;
    agent_name: string;
    registration_date: string;
}

const ModelSelector: React.FC<ModelSelectorProps> = ({ onSelectModel }) => {
    const [models, setModels] = useState<Model[]>([]);
    const [isLoading, setIsLoading] = useState<boolean>(true);

    useEffect(() => {
        const fetchModels = async () => {
            try {
                const response = await fetch('/api/rl/models');
                const data = await response.json();
                setModels(data.models || []);
            } catch (error) {
                console.error("Failed to fetch models:", error);
            } finally {
                setIsLoading(false);
            }
        };
        fetchModels();
    }, []);

    return (
        <div>
            <h3 className="text-lg font-semibold mb-2">Select a Trained Model</h3>
            {isLoading ? (
                <p>Loading models...</p>
            ) : (
                <select
                    onChange={(e) => onSelectModel(e.target.value)}
                    className="bg-gray-700 text-white p-2 rounded w-full"
                >
                    <option value="">-- Choose a model --</option>
                    {models.map((model) => (
                        <option key={model.id} value={model.id}>
                            {model.agent_name} ({model.id})
                        </option>
                    ))}
                </select>
            )}
        </div>
    );
};

export default ModelSelector;