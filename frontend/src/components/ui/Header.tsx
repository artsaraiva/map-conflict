"use client";

interface HeaderProps {
  eventCount: number;
  onRefresh: () => void;
  isRefreshing: boolean;
}

export default function Header({
  eventCount,
  onRefresh,
  isRefreshing,
}: HeaderProps) {
  return (
    <header className="absolute top-0 left-0 right-0 z-40 flex h-16 items-center justify-between border-b border-[#33444b]/70 bg-[linear-gradient(180deg,rgba(7,14,19,0.96),rgba(9,16,20,0.82))] px-4 text-[#dbe2e2] shadow-[0_12px_30px_rgba(0,0,0,0.28)] backdrop-blur-md">
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-[#5d4638] bg-[radial-gradient(circle_at_top,#ff9860,#7f2f21_70%)] shadow-[0_0_22px_rgba(255,113,77,0.35)]">
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="white"
              strokeWidth="2"
            >
              <circle cx="12" cy="12" r="10" />
              <path d="M2 12h20M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
            </svg>
          </div>
          <div>
            <div className="text-[10px] uppercase tracking-[0.34em] text-[#78969f]">
              Strategic Monitor
            </div>
            <h1 className="text-base font-bold leading-none text-[#f3ebdc]">
              World Tension Watch
            </h1>
            <p className="text-[10px] uppercase tracking-[0.24em] text-[#8ea1a8]">
              Live geopolitical signal board
            </p>
          </div>
        </div>
      </div>

      <div className="flex items-center gap-2 md:gap-3">
        <div className="hidden items-center gap-2 rounded-xl border border-[#34434a] bg-[#101920]/75 px-3 py-2 md:flex">
          <div className="h-2.5 w-2.5 rounded-full bg-[#57d7a7] shadow-[0_0_16px_rgba(87,215,167,0.8)] animate-pulse" />
          <span className="text-[11px] uppercase tracking-[0.22em] text-[#8ea0a5]">
            <span className="font-semibold text-[#f3ebdc]">{eventCount}</span> active signals
          </span>
        </div>

        <button
          onClick={onRefresh}
          disabled={isRefreshing}
          className="flex items-center gap-1.5 rounded-xl border border-[#43515a] bg-[linear-gradient(180deg,rgba(24,34,41,0.95),rgba(14,23,29,0.95))] px-3 py-2 text-[11px] uppercase tracking-[0.18em] text-[#c3cfd0] transition-all hover:border-[#5e6a72] hover:text-[#f0eadb] disabled:opacity-50"
        >
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            className={isRefreshing ? "animate-spin" : ""}
          >
            <path d="M23 4v6h-6M1 20v-6h6" />
            <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
          </svg>
          {isRefreshing ? "Refreshing" : "Refresh Map"}
        </button>
      </div>
    </header>
  );
}
