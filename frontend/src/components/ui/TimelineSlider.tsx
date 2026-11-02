"use client";

import { useState, useCallback, useMemo } from "react";
import clsx from "clsx";

interface TimelineSliderProps {
  eventTimes: string[];
  onTimeChange: (cursor: Date | null) => void;
}

const STEPS = 48;

// Initialiser runs once on first render — avoids impure-function-in-render lint error
function getInitialNow() {
  return Date.now();
}

export default function TimelineSlider({ eventTimes, onTimeChange }: TimelineSliderProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [position, setPosition] = useState(STEPS);
  // Capture session start time once (lazy-init so it only runs on mount)
  const [sessionStart] = useState<number>(getInitialNow);

  const oldestTime = useMemo(() => {
    if (eventTimes.length === 0) return sessionStart - 72 * 3600 * 1000;
    return Math.min(...eventTimes.map((t) => new Date(t).getTime()));
  }, [eventTimes, sessionStart]);

  const totalRange = sessionStart - oldestTime;

  const cursorTime = useMemo(() => {
    if (position === STEPS) return null;
    const ratio = position / STEPS;
    return new Date(oldestTime + ratio * totalRange);
  }, [position, oldestTime, totalRange]);

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const val = parseInt(e.target.value, 10);
      setPosition(val);
      const ratio = val / STEPS;
      const ts = val === STEPS ? null : new Date(oldestTime + ratio * totalRange);
      onTimeChange(ts);
    },
    [oldestTime, totalRange, onTimeChange]
  );

  const reset = useCallback(() => {
    setPosition(STEPS);
    onTimeChange(null);
  }, [onTimeChange]);

  // Format the cursor label
  const cursorLabel = cursorTime
    ? cursorTime.toLocaleString("en-US", {
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      })
    : "Live";

  const isReplaying = position < STEPS;

  return (
    <div className="absolute bottom-8 left-1/2 z-40 -translate-x-1/2">
      {/* Toggle button */}
      {!isOpen && (
        <button
          onClick={() => setIsOpen(true)}
          className="flex items-center gap-2 rounded-xl border border-[#3a4b52] bg-[#111920]/92 px-3.5 py-2 text-[11px] uppercase tracking-[0.22em] text-[#94a6aa] backdrop-blur-md transition-all hover:border-[#5c6970] hover:text-[#eef1e9]"
        >
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10" />
            <polyline points="12 6 12 12 16 14" />
          </svg>
          Timeline
        </button>
      )}

      {/* Expanded slider panel */}
      {isOpen && (
        <div className="flex w-[420px] flex-col gap-3 rounded-2xl border border-[#3a4b52] bg-[#0d1820]/95 px-5 py-4 backdrop-blur-md shadow-xl">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke={isReplaying ? "#75d1ff" : "#94a6aa"} strokeWidth="2">
                <circle cx="12" cy="12" r="10" />
                <polyline points="12 6 12 12 16 14" />
              </svg>
              <span className="text-[10px] uppercase tracking-[0.3em] text-[#7f9aa3]">
                Timeline Replay
              </span>
            </div>
            <div className="flex items-center gap-2">
              {isReplaying && (
                <button
                  onClick={reset}
                  className="text-[10px] uppercase tracking-wider text-[#75d1ff] hover:text-[#9fe4ff] transition-colors"
                >
                  Live
                </button>
              )}
              <button
                onClick={() => { setIsOpen(false); reset(); }}
                className="rounded-lg p-1 text-[#5d7078] hover:text-[#94a6aa] transition-colors"
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M18 6L6 18M6 6l12 12" />
                </svg>
              </button>
            </div>
          </div>

          {/* Cursor label */}
          <div className="text-center">
            <span
              className={clsx(
                "text-sm font-semibold tracking-wide",
                isReplaying ? "text-[#75d1ff]" : "text-[#d0e8ef]"
              )}
            >
              {cursorLabel}
            </span>
            {isReplaying && (
              <span className="ml-2 text-[11px] text-[#5d7078]">
                — showing events up to this point
              </span>
            )}
          </div>

          {/* Slider */}
          <div className="relative px-1">
            <input
              type="range"
              min={0}
              max={STEPS}
              step={1}
              value={position}
              onChange={handleChange}
              className="w-full appearance-none cursor-pointer h-1 rounded-full outline-none"
              style={{
                background: `linear-gradient(to right, #75d1ff ${(position / STEPS) * 100}%, #253038 ${(position / STEPS) * 100}%)`,
              }}
            />
            {/* Tick marks */}
            <div className="mt-1.5 flex justify-between px-0">
              <span className="text-[9px] text-[#4d6068]">Oldest</span>
              <span className="text-[9px] text-[#4d6068]">Now</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
