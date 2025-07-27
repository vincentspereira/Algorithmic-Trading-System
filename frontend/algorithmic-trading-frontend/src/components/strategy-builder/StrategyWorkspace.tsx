"use client";

import { useEffect, useRef } from 'react';
import Blockly, { Themes } from 'blockly/core';
import 'blockly/blocks';
import '@/components/blockly/blocks/indicators';
import '@/components/blockly/blocks/conditions';
import '@/components/blockly/blocks/actions';
import '@/components/blockly/blocks/risk';
import { toolbox } from '@/components/blockly/toolbox';

interface StrategyWorkspaceProps {
  onWorkspaceChange: (workspace: Blockly.Workspace) => void;
}

const StrategyWorkspace = ({ onWorkspaceChange }: StrategyWorkspaceProps) => {
  const blocklyDiv = useRef<HTMLDivElement>(null);
  const workspace = useRef<Blockly.WorkspaceSvg | null>(null);

  useEffect(() => {
    if (blocklyDiv.current && !workspace.current) {
      const newWorkspace = Blockly.inject(blocklyDiv.current, {
        toolbox: toolbox,
        theme: Themes.Dark,
        readOnly: false,
        move: {
          scrollbars: true,
          drag: true,
          wheel: true,
        },
        grid: {
          spacing: 20,
          length: 3,
          colour: '#ccc',
          snap: true,
        },
      });
      workspace.current = newWorkspace;
      newWorkspace.addChangeListener(() => onWorkspaceChange(newWorkspace));
    }

    return () => {
      if (workspace.current) {
        workspace.current.dispose();
        workspace.current = null;
      }
    };
  }, [onWorkspaceChange]);

  return (
    <div
      id="blocklyDiv"
      ref={blocklyDiv}
      style={{ height: '100%', width: '100%' }}
    />
  );
};

export default StrategyWorkspace;