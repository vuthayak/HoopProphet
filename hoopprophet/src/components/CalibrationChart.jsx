import React from 'react';
import { ParentSize } from '@visx/responsive';
import { scaleLinear } from '@visx/scale';
import { LinePath, Circle } from '@visx/shape';
import { AxisBottom, AxisLeft } from '@visx/axis';
import { Group } from '@visx/group';

const CHART_HEIGHT = 280;
const PADDING = { top: 20, right: 20, bottom: 40, left: 50 };

function CalibrationChartInner({ data, width }) {
  const height = CHART_HEIGHT;
  const chartW = width - PADDING.left - PADDING.right;
  const chartH = height - PADDING.top - PADDING.bottom;

  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 text-text-muted text-sm">
        Calibration data not available.
      </div>
    );
  }

  const xScale = scaleLinear({ domain: [0, 1], range: [0, chartW] });
  const yScale = scaleLinear({ domain: [0, 1], range: [chartH, 0] });

  const perfectLine = [
    { x: 0, y: 0 },
    { x: 1, y: 1 },
  ];

  return (
    <svg width={width} height={height}>
      <Group left={PADDING.left} top={PADDING.top}>
        {[0.2, 0.4, 0.6, 0.8, 1].map(tick => (
          <line
            key={tick}
            x1={0}
            x2={chartW}
            y1={yScale(tick)}
            y2={yScale(tick)}
            stroke="#334155"
            strokeDasharray="4,4"
          />
        ))}
        <AxisLeft
          scale={yScale}
          tickFormat={v => `${Math.round(v * 100)}%`}
          tickValues={[0, 0.2, 0.4, 0.6, 0.8, 1]}
          stroke="#64748b"
          tickStroke="#64748b"
          tickLabelProps={{ fill: '#64748b', fontSize: 10 }}
        />
        <AxisBottom
          scale={xScale}
          top={chartH}
          tickFormat={v => `${Math.round(v * 100)}%`}
          tickValues={[0, 0.2, 0.4, 0.6, 0.8, 1]}
          stroke="#64748b"
          tickStroke="#64748b"
          tickLabelProps={{ fill: '#64748b', fontSize: 10 }}
        />
        <LinePath
          data={perfectLine}
          x={d => xScale(d.x)}
          y={d => yScale(d.y)}
          stroke="#64748b"
          strokeDasharray="6,4"
          strokeWidth={1.5}
        />
        <LinePath
          data={data}
          x={d => xScale(d.predicted_bin)}
          y={d => yScale(d.observed_pct)}
          stroke="#3b82f6"
          strokeWidth={2}
        />
        {data.map((d, i) => (
          <Circle
            key={i}
            cx={xScale(d.predicted_bin)}
            cy={yScale(d.observed_pct)}
            r={4}
            fill="#3b82f6"
          />
        ))}
      </Group>
    </svg>
  );
}

export default function CalibrationChart({ data }) {
  return (
    <ParentSize>
      {({ width }) => <CalibrationChartInner data={data} width={width || 400} />}
    </ParentSize>
  );
}