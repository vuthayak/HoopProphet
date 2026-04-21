import { useState } from 'react';
import { PROB_THRESHOLDS } from '../utils/constants';

export default function LineSlider({ stat, defaultLine, onLineChange }) {
  const [line, setLine] = useState(defaultLine);

  function handleChange(e) {
    const val = parseFloat(e.target.value);
    setLine(val);
  }

  function handleRelease() {
    onLineChange(line);
  }

  const min = defaultLine - 10;
  const max = defaultLine + 10;
  const fillPct = ((line - min) / (max - min)) * 100;

  return (
    <div className="w-full">
      <div className="flex justify-between text-xs text-text-muted mb-1">
        <span>{stat}</span>
        <span className="font-medium text-text-primary">{line}</span>
      </div>
      <div className="relative">
        <div className="absolute top-1/2 left-0 right-0 h-1 bg-slate-700 rounded-full -translate-y-1/2" />
        <div
          className="absolute top-1/2 left-0 h-1 bg-accent rounded-full -translate-y-1/2"
          style={{ width: `${fillPct}%` }}
        />
        <input
          type="range"
          min={min}
          max={max}
          step="0.5"
          value={line}
          onChange={handleChange}
          onMouseUp={handleRelease}
          onTouchEnd={handleRelease}
          aria-label={`Adjust ${stat} line`}
          className="relative w-full h-5 appearance-none bg-transparent cursor-pointer z-10"
          style={{
            WebkitAppearance: 'none',
          }}
        />
      </div>
    </div>
  );
}