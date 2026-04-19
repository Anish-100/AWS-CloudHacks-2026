import logo from "../Images/logo.png";

export default function AppShell({ apiMode, uploadStatus, children }) {
  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="topbar__brand">
          <img src={logo} alt="Pyran logo" className="topbar__logo" style={{ height: "30px", width: "auto" }} />
          <p className="eyebrow">Pyran</p>
          <div>
            <h1>Short-term financial planner</h1>
          </div>
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