type StatusPillProps = {
  tone: "success" | "danger" | "neutral" | "warning";
  children: string;
};

export function StatusPill({ tone, children }: StatusPillProps) {
  return <span className={`status-pill ${tone}`}>{children}</span>;
}
