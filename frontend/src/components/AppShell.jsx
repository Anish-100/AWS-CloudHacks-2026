export default function AppShell({ apiMode, uploadStatus, children }) {
  return (
    <div className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">Puran</p>
          <h1>Short-term financial planner</h1>
        </div>
        <div className="topbar__meta">
          <span>{apiMode}</span>
          <span>{uploadStatus}</span>
        </div>
      </header>
      {children}
    </div>
  );
}
