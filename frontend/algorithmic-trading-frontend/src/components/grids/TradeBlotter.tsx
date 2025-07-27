"use client";

import React from 'react';
import { AgGridReact } from 'ag-grid-react';
import { ColDef } from 'ag-grid-community';
import 'ag-grid-community/styles/ag-grid.css';
import 'ag-grid-community/styles/ag-theme-alpine.css';
import { Trade } from '@/types/trading';

interface TradeBlotterProps {
  trades: Trade[];
}

const TradeBlotter: React.FC<TradeBlotterProps> = ({ trades }) => {
  const columnDefs: ColDef[] = [
    { field: 'id', headerName: 'Trade ID' },
    { field: 'symbol', headerName: 'Symbol' },
    { field: 'quantity', headerName: 'Quantity' },
    { field: 'price', headerName: 'Price' },
    { field: 'side', headerName: 'Side' },
    { field: 'timestamp', headerName: 'Timestamp' },
  ];

  return (
    <div className="ag-theme-alpine-dark" style={{ height: 400, width: '100%' }}>
      <AgGridReact
        rowData={trades}
        columnDefs={columnDefs}
      />
    </div>
  );
};

export default TradeBlotter;