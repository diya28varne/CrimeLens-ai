/** Stylized Karnataka State Police emblem for CrimeLens UI (branding mark). */
export function KarnatakaPoliceEmblem({ size = 44 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 64 64"
      role="img"
      aria-label="Karnataka State Police"
      style={{ flexShrink: 0, display: "block" }}
    >
      <defs>
        <linearGradient id="kspGold" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#f5d76e" />
          <stop offset="55%" stopColor="#c9a227" />
          <stop offset="100%" stopColor="#8a6b12" />
        </linearGradient>
        <linearGradient id="kspBlue" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#1e4d8c" />
          <stop offset="100%" stopColor="#0b2140" />
        </linearGradient>
      </defs>
      {/* Outer star / badge */}
      <path
        d="M32 2 L38 18 L55 18 L41 28 L47 45 L32 35 L17 45 L23 28 L9 18 L26 18 Z"
        fill="url(#kspGold)"
        stroke="#f8e7a0"
        strokeWidth="1"
      />
      <circle cx="32" cy="30" r="14" fill="url(#kspBlue)" stroke="#f5d76e" strokeWidth="2" />
      <circle cx="32" cy="30" r="10" fill="none" stroke="#f5d76e" strokeWidth="1" opacity="0.7" />
      {/* Ashoka-style wheel hint */}
      <circle cx="32" cy="30" r="4.5" fill="none" stroke="#f5d76e" strokeWidth="1.2" />
      <g stroke="#f5d76e" strokeWidth="1">
        <line x1="32" y1="25.5" x2="32" y2="34.5" />
        <line x1="27.5" y1="30" x2="36.5" y2="30" />
        <line x1="28.8" y1="26.8" x2="35.2" y2="33.2" />
        <line x1="35.2" y1="26.8" x2="28.8" y2="33.2" />
      </g>
      {/* Ribbon */}
      <path
        d="M18 48 H46 L43 54 H21 Z"
        fill="url(#kspGold)"
        stroke="#f8e7a0"
        strokeWidth="0.8"
      />
      <text
        x="32"
        y="52.2"
        textAnchor="middle"
        fill="#0b2140"
        fontSize="5.5"
        fontWeight="700"
        fontFamily="Segoe UI, sans-serif"
      >
        KSP
      </text>
    </svg>
  );
}
