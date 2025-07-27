"use client";

import React from 'react';
import { ChartCanvas, Chart } from 'react-financial-charts';
import { CandlestickSeries } from 'react-financial-charts';
import { XAxis, YAxis } from 'react-financial-charts';
import { discontinuousTimeScaleProvider } from 'react-financial-charts';
import { OHLCTooltip } from 'react-financial-charts';
import { fitWidth } from 'react-financial-charts';
import { MarketData } from '@/types/trading';

interface CandlestickChartProps {
  data: MarketData[];
  width: number;
  ratio: number;
}

const CandlestickChart: React.FC<CandlestickChartProps> = ({ data, width, ratio }) => {
  if (!data || data.length === 0) {
    return <div className="text-center p-4">No data to display</div>;
  }
  const xScaleProvider = discontinuousTimeScaleProvider.inputDateAccessor(
    (d: MarketData) => d.date
  );
  const {
    data: chartData,
    xScale,
    xAccessor,
    displayXAccessor,
  } = xScaleProvider(data);

  return (
    <ChartCanvas
      height={400}
      ratio={ratio}
      width={width}
      margin={{ left: 50, right: 50, top: 10, bottom: 30 }}
      data={chartData}
      xScale={xScale}
      xAccessor={xAccessor}
      displayXAccessor={displayXAccessor}
      seriesName="MSFT"
    >
      <Chart id={1} yExtents={(d: MarketData) => [d.high, d.low]}>
        <XAxis axisAt="bottom" orient="bottom" />
        <YAxis axisAt="left" orient="left" ticks={5} />
        <CandlestickSeries fill={(d: MarketData) => (d.close > d.open ? "#26a69a" : "#ef5350")} />
        <OHLCTooltip origin={[-40, 0]} textFill="#FFFFFF" />
      </Chart>
    </ChartCanvas>
  );
};

export default fitWidth(CandlestickChart);