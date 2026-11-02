"use client";

import { useState } from "react";
import { VISUAL_FAMILY_CONFIG } from "@/lib/types";

export default function LegendPanel() {
  const [isOpen, setIsOpen] = useState(false);
  const families = Object.entries(VISUAL_FAMILY_CONFIG);

  return (
    <div className="absolute right-3 bottom-12 z-30 max-md:hidden">
      {/* Collapsed: small icon button */}
      {!isOpen && (
        <button
          onClick={() => setIsOpen(true)}
          className="flex h-10 w-10 items-center justify-center rounded-xl border border-[#33434a]/75 bg-[rgba(10,18,24,0.92)] text-[#8ca0a4] shadow-[0_8px_24px_rgba(0,0,0,0.3)] backdrop-blur-md transition-colors hover:bg-[rgba(18,28,34,0.95)] hover:text-[#c8d4d4]"
          title="Show legend"
        >
          {/* Layers icon */}
          <svg
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <polygon points="12 2 2 7 12 12 22 7 12 2" />
            <polyline points="2 17 12 22 22 17" />
            <polyline points="2 12 12 17 22 12" />
          </svg>
        </button>
      )}

      {/* Expanded: compact legend */}
      {isOpen && (
        <aside className="w-[200px] rounded-xl border border-[#33434a]/75 bg-[rgba(10,18,24,0.94)] p-3 text-[#d6dddd] shadow-[0_12px_32px_rgba(0,0,0,0.35)] backdrop-blur-md">
          <div className="mb-2 flex items-center justify-between">
            <span className="text-[10px] font-semibold uppercase tracking-[0.3em] text-[#7a9aa3]">
              Legend
            </span>
            <button
              onClick={() => setIsOpen(false)}
              className="flex h-5 w-5 items-center justify-center rounded text-[#7a9aa3] transition-colors hover:text-[#c8d4d4]"
              title="Collapse legend"
            >
              <svg
                width="12"
                height="12"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          </div>

          <div className="space-y-1">
            {families.map(([family, config]) => (
              <div key={family} className="flex items-center gap-2 py-0.5">
                <span
                  className="h-2 w-2 flex-shrink-0 rounded-full shadow-[0_0_8px_currentColor]"
                  style={{ backgroundColor: config.color, color: config.color }}
                />
                <span className="text-[11px] uppercase tracking-[0.14em] text-[#c8d4d4]">
                  {config.label}
                </span>
              </div>
            ))}
          </div>

          <div className="mt-3 border-t border-[#33434a]/75 pt-2">
            <span className="text-[10px] font-semibold uppercase tracking-[0.3em] text-[#7a9aa3]">
              Pressure
            </span>
            <div
              className="mt-1.5 h-2 rounded-sm"
              style={{ background: "linear-gradient(90deg, rgba(255,105,74,0.04), rgba(255,105,74,0.2))" }}
            />
            <div className="mt-0.5 flex justify-between text-[9px] uppercase tracking-[0.14em] text-[#7a9aa3]">
              <span>Least</span>
              <span>Most</span>
            </div>
            <div className="mt-1.5 flex items-center gap-2 py-0.5">
              <span className="h-2.5 w-4 flex-shrink-0 rounded-sm border border-dashed border-[rgb(255,105,74)]" />
              <span className="text-[11px] uppercase tracking-[0.14em] text-[#c8d4d4]">
                Escalating
              </span>
            </div>
          </div>
        </aside>
      )}
    </div>
  );
}
