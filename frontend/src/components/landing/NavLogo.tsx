export function NavLogo({ size = 28 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 28 28" fill="none" aria-hidden="true">
      <rect x="2" y="2" width="11" height="9" rx="2.5" fill="var(--primary)" />
      <rect
        x="15"
        y="2"
        width="11"
        height="9"
        rx="2.5"
        fill="color-mix(in oklch, var(--primary) 55%, #2563eb)"
      />
      <rect
        x="8.5"
        y="17"
        width="11"
        height="9"
        rx="2.5"
        fill="var(--muted)"
        stroke="var(--primary)"
        strokeWidth="1.4"
      />
      <path d="M7.5 11V14a2 2 0 0 0 2 2h6" stroke="var(--primary)" strokeWidth="1.4" fill="none" />
      <path
        d="M20.5 11V14a2 2 0 0 1-2 2h-4"
        stroke="color-mix(in oklch, var(--primary) 55%, #2563eb)"
        strokeWidth="1.4"
        fill="none"
      />
    </svg>
  );
}
