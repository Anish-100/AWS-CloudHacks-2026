function buildForest(goals) {
  const trees = [];

  goals.forEach((goal) => {
    if (goal.status === "achieved") {
      trees.push({ label: "tree", className: "tree achieved", icon: "▲" });
    } else if (goal.status === "failed") {
      trees.push({ label: "burned tree", className: "tree failed", icon: "♠" });
    } else {
      trees.push({ label: "sapling", className: "tree pending", icon: "♣" });
    }
  });

  return trees;
}

export default function ForestCanvas({ goals }) {
  const forest = buildForest(goals);
  const achieved = goals.filter((goal) => goal.status === "achieved").length;
  const pending = goals.filter((goal) => goal.status === "pending").length;
  const failed = goals.filter((goal) => goal.status === "failed").length;

  return (
    <section className="forest-panel">
      <div className="forest-image" aria-hidden="true">
        <img
          src="https://images.unsplash.com/photo-1448375240586-882707db888b?auto=format&fit=crop&w=1200&q=80"
          alt=""
        />
      </div>
      <div className="forest-content">
        <div className="section-heading">
          <p className="eyebrow">Goal forest</p>
          <h2>Your habits grow here.</h2>
        </div>

        <div className="forest-ground" aria-label="Goal forest status">
          {forest.length ? (
            forest.map((tree, index) => (
              <span key={`${tree.label}-${index}`} className={tree.className} aria-label={tree.label}>
                {tree.icon}
              </span>
            ))
          ) : (
            <p className="empty-state">Create a goal to plant the first sapling.</p>
          )}
        </div>

        <div className="forest-stats">
          <span>{achieved} achieved</span>
          <span>{pending} active</span>
          <span>{failed} failed</span>
        </div>
      </div>
    </section>
  );
}
