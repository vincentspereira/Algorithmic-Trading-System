import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import PredictionWidget from '../PredictionWidget';

describe('PredictionWidget', () => {
    const mockPredictions = {
        '1min': { prediction: 250.50, confidence: 0.95 },
        '5min': { prediction: 252.00, confidence: 0.80 },
        '15min': { prediction: 248.75, confidence: 0.60 },
    };

    const symbol = "MOCK.SYMBOL";
    const lastUpdated = new Date().toISOString();

    it('renders the symbol and title correctly', () => {
        render(<PredictionWidget symbol={symbol} predictions={mockPredictions} lastUpdated={lastUpdated} />);
        expect(screen.getByText(`${symbol} Predictions`)).toBeInTheDocument();
    });

    it('displays the "Loading predictions..." message when predictions are null', () => {
        render(<PredictionWidget symbol={symbol} predictions={null} lastUpdated={null} />);
        expect(screen.getByText('Loading predictions...')).toBeInTheDocument();
    });

    it('renders all prediction horizons with correct data', () => {
        render(<PredictionWidget symbol={symbol} predictions={mockPredictions} lastUpdated={lastUpdated} />);
        
        // Check for 1min prediction
        expect(screen.getByText('1min')).toBeInTheDocument();
        expect(screen.getByText('250.50')).toBeInTheDocument();
        expect(screen.getByText('95.0%')).toBeInTheDocument();

        // Check for 5min prediction
        expect(screen.getByText('5min')).toBeInTheDocument();
        expect(screen.getByText('252.00')).toBeInTheDocument();
        expect(screen.getByText('80.0%')).toBeInTheDocument();

        // Check for 15min prediction
        expect(screen.getByText('15min')).toBeInTheDocument();
        expect(screen.getByText('248.75')).toBeInTheDocument();
        expect(screen.getByText('60.0%')).toBeInTheDocument();
    });

    it('applies the correct color based on confidence scores', () => {
        const { rerender } = render(<PredictionWidget symbol={symbol} predictions={mockPredictions} lastUpdated={lastUpdated} />);

        // High confidence (>= 0.8) -> green
        expect(screen.getByText('95.0%')).toHaveClass('text-green-400');
        expect(screen.getByText('80.0%')).toHaveClass('text-green-400');

        // Medium confidence (>= 0.65) -> yellow
        const mediumConfidencePredictions = { ...mockPredictions, '5min': { prediction: 252.00, confidence: 0.70 }};
        rerender(<PredictionWidget symbol={symbol} predictions={mediumConfidencePredictions} lastUpdated={lastUpdated} />);
        expect(screen.getByText('70.0%')).toHaveClass('text-yellow-400');
        
        // Low confidence (< 0.65) -> red
        const lowConfidencePredictions = { ...mockPredictions, '15min': { prediction: 248.75, confidence: 0.60 }};
        rerender(<PredictionWidget symbol={symbol} predictions={lowConfidencePredictions} lastUpdated={lastUpdated} />);
        expect(screen.getByText('60.0%')).toHaveClass('text-red-400');
    });

    it('displays the last updated time correctly', () => {
        const date = new Date(lastUpdated);
        render(<PredictionWidget symbol={symbol} predictions={mockPredictions} lastUpdated={lastUpdated} />);
        expect(screen.getByText(date.toLocaleTimeString())).toBeInTheDocument();
    });
});