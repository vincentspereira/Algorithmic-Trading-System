"use client";

import { useEffect, useRef, useState } from 'react';
import Blockly, { Themes } from 'blockly/core';
import 'blockly/blocks';
import '@/components/blockly/blocks/indicators';
import '@/components/blockly/blocks/conditions';
import '@/components/blockly/blocks/actions';
import '@/components/blockly/blocks/risk';
import { toolbox } from '@/components/blockly/toolbox';
import StrategyWorkspace from '@/components/strategy-builder/StrategyWorkspace';
import CodePreview from '@/components/strategy-builder/CodePreview';
import StrategyTester from '@/components/strategy-builder/StrategyTester';
import { generateStrategyCode } from '@/utils/strategyGenerator';

const StrategyBuilderPage = () => {
  const [code, setCode] = useState('');
  const [workspace, setWorkspace] = useState<Blockly.Workspace | null>(null);
  const [backtestResults, setBacktestResults] = useState(null);

  const handleWorkspaceChange = (newWorkspace: Blockly.Workspace) => {
    setWorkspace(newWorkspace);
    const newCode = generateStrategyCode(newWorkspace);
    setCode(newCode);
  };

  const handleBacktest = async () => {
    const response = await fetch('/api/v1/strategy-builder/strategy/backtest', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ code }),
    });
    const results = await response.json();
    setBacktestResults(results);
  };

  return (
    <div style={{ display: 'flex', height: '100vh' }}>
      <div style={{ width: '70%', height: '100%' }}>
        <StrategyWorkspace onWorkspaceChange={handleWorkspaceChange} />
      </div>
      <div style={{ width: '30%', padding: '10px' }}>
        <CodePreview code={code} />
        <button onClick={handleBacktest}>Run Backtest</button>
        <StrategyTester results={backtestResults} />
      </div>
    </div>
  );
};

export default StrategyBuilderPage;