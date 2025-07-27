import React from 'react';

interface Prediction {
  prediction: number;
  confidence: number;
}

interface PredictionsData {
  '1min': Prediction;
  '5min': Prediction;
  '15min': Prediction;
}

interface PredictionWidgetProps {
  symbol: string;
  predictions: PredictionsData | null;
  lastUpdated: string | null;
}

const PredictionWidget: React.FC<PredictionWidgetProps> = ({ symbol, predictions, lastUpdated }) => {
  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'text-green-400';
    if (confidence >= 0.65) return 'text-yellow-400';
    return 'text-red-400';
  };

  const renderPredictionRow = (horizon: keyof PredictionsData, data: Prediction) => (
    <div key={horizon} className="flex justify-between items-center py-2 border-b border-gray-700 last:border-b-0">
      <span className="text-sm font-medium text-gray-300">{horizon}</span>
      <span className="text-md font-semibold text-white">
        {data.prediction.toFixed(2)}
      </span>
      <span className={`text-sm font-medium ${getConfidenceColor(data.confidence)}`}>
        {(data.confidence * 100).toFixed(1)}%
      </span>
    </div>
  );

  return (
    <div className="bg-gray-800 p-4 rounded-lg shadow-lg w-full max-w-sm mx-auto">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-bold text-white">{symbol} Predictions</h3>
        {lastUpdated && (
          <span className="text-xs text-gray-400">
            {new Date(lastUpdated).toLocaleTimeString()}
          </span>
        )}
      </div>
      {predictions ? (
        <div className="space-y-2">
          {Object.entries(predictions).map(([horizon, data]) =>
            renderPredictionRow(horizon as keyof PredictionsData, data)
          )}
        </div>
      ) : (
        <div className="text-center py-4 text-gray-400">
          Loading predictions...
        </div>
      )}
    </div>
  );
};

// Example of how this component might be used with mock data
export const MockPredictionWidget: React.FC = () => {
  const mockPredictions: PredictionsData = {
    '1min': { prediction: 175.25, confidence: 0.88 },
    '5min': { prediction: 175.80, confidence: 0.75 },
    '15min': { prediction: 174.90, confidence: 0.62 },
  };
  
  return (
    <div className="p-8 bg-gray-900">
      <PredictionWidget 
        symbol="AAPL" 
        predictions={mockPredictions}
        lastUpdated={new Date().toISOString()}
      />
    </div>
  );
};

export default PredictionWidget;