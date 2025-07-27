"use client";

import { useRef } from 'react';

const StrategyToolbox = () => {
    const toolboxRef = useRef<HTMLDivElement>(null);

    return (
        <div ref={toolboxRef} style={{ display: 'none' }}>
            {/* Toolbox configuration will be added here */}
        </div>
    );
};

export default StrategyToolbox;