import logo from "../Images/logo.png";

export default function AppShell({ apiMode, uploadStatus, children }) {
  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="topbar__brand">
          <img src={logo} alt="Puran logo" className="topbar__logo" style={{ height: "50px", width: "auto" }} />
        </div>
        <div style={{ position: "absolute", left: "9%", transform: "translateX(-50%)" }}>
          <span style={{ color: "white", fontSize: "30px", fontWeight: "bold" }}>Puran</span>
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