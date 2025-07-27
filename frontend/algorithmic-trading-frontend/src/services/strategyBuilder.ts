export const saveStrategy = async (name: string, description: string, code: string) => {
    const response = await fetch('/api/v1/strategy-builder/strategy/save', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ name, description, code }),
    });
    return response.json();
};

export const loadStrategies = async () => {
    const response = await fetch('/api/v1/strategy-builder/strategy/list');
    return response.json();
};

export const validateStrategy = async (code: string) => {
    const response = await fetch('/api/v1/strategy-builder/strategy/validate', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ code }),
    });
    return response.json();
};

export const backtestStrategy = async (code: string) => {
    const response = await fetch('/api/v1/strategy-builder/strategy/backtest', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ code }),
    });
    return response.json();
};

export const deployStrategy = async (strategyId: number) => {
    // Placeholder for deploying a strategy
    console.log(`Deploying strategy ${strategyId}`);
    return Promise.resolve({ status: 'success', message: 'Strategy deployed successfully' });
};