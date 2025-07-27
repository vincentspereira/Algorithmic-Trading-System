"use client";

interface StrategyTesterProps {
    results: any;
}

const StrategyTester = ({ results }: StrategyTesterProps) => {
    return (
        <div>
            <h2>Backtest Results</h2>
            <pre>
                {JSON.stringify(results, null, 2)}
            </pre>
        </div>
    );
};

export default StrategyTester;