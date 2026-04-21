import { useEffect, useRef } from 'react';
import { ParentSize } from '@visx/responsive';
import { scaleBand, scaleLinear } from '@visx/scale';
import { Bar } from '@visx/shape';
import { AxisBottom, AxisLeft } from '@visx/axis';
import { Group } from '@visx/group';

const WINDOWS = ['L5', 'L10', 'L20', 'Season'];
const CHART_WIDTH = 240;
const CHART_HEIGHT = 160;
const PADDING = { top: 16, right: 16, bottom: 32, left: 32 };

function getBarColor(rate) {
  if (rate === null || rate === undefined) return '#64748b';
  if (rate >= 0.55) return '#22c55e';
  if (rate >= 0.40) return '#eab308';
  return '#ef4444';
}

function HitRateChartInner({ data, width, height }) {
  const chartW = width - PADDING.left - PADDING.right;
  const chartH = height - PADDING.top - PADDING.bottom;

  const xScale = scaleBand({
    domain: WINDOWS,
    range: [0, chartW],
    padding: 0.3,
  });

  const yScale = scaleLinear({
    domain: [0, 1],
    range: [chartH, 0],
  });

  return (
    <svg width={width} height={height}>
      <Group left={PADDING.left} top={PADDING.top}>
        {[0.25, 0.5, 0.75, 1].map(tick => (
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
          tickValues={[0, 0.25, 0.5, 0.75, 1]}
          stroke="#64748b"
          tickStroke="#64748b"
          tickLabelProps={{ fill: '#64748b', fontSize: 10 }}
        />
        <AxisBottom
          scale={xScale}
          top={chartH}
          stroke="#64748b"
          tickStroke="#64748b"
          tickLabelProps={{ fill: '#64748b', fontSize: 10 }}
        />
        {WINDOWS.map((win, i) => {
          const hitRate = data?.hit_rates?.[win];
          const rate = hitRate?.rate;
          const count = hitRate?.count || 0;
          if (rate === null || rate === undefined) {
            return (
              <text
                key={win}
                x={xScale(win) + xScale.bandwidth() / 2}
                y={chartH / 2}
                textAnchor="middle"
                fill="#64748b"
                fontSize={12}
              >
                —
              </text>
            );
          }
          const barH = chartH - yScale(rate);
          return (
            <Group key={win}>
              <Bar
                x={xScale(win)}
                y={yScale(rate)}
                width={xScale.bandwidth()}
                height={barH}
                fill={getBarColor(rate)}
                rx={2}
              />
            </Group>
          );
        })}
      </Group>
    </svg>
  );
}

export default function HitRateChart({ data }) {
  return (
    <ParentSize>
      {({ width }) => (
        <HitRateChartInner data={data} width={width || CHART_WIDTH} height={CHART_HEIGHT} />
      )}
    </ParentSize>
  );
}