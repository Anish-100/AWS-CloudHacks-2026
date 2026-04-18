export default function QuickSightPanel({ embedUrl, isLoading }) {
  return (
    <section className="quicksight-panel">
      <div className="section-heading">
        <p className="eyebrow">QuickSight</p>
        <h2>Spending patterns.</h2>
      </div>

      {embedUrl ? (
        <iframe title="QuickSight spending dashboard" src={embedUrl} />
      ) : (
        <div className="quicksight-placeholder">
          <p>{isLoading ? "Loading dashboard..." : "Connect QuickSight to show embedded charts here."}</p>
        </div>
      )}
    </section>
  );
}
