import moneyTree from "../Images/pyranMoneyTree.png";
import burntMoneyTree from "../Images/pyranMoneyTreeBurnt.png";

function getGoalProgress(goal) {
  const target = Number(goal.targetAmount || 0);
  const current = Number(goal.currentAmount || 0);

  if (target <= 0) {
    return 0;
  }

  return Math.min(Math.max(current / target, 0), 1);
}

function buildForest(goals) {
  return goals.map((goal) => {
    const progress = getGoalProgress(goal);
    const intensity = goal.status === "pending" ? Math.max(0.12, 1 - progress) : 0;
    const fireStyle = {
      "--fire-intensity": intensity,
      "--fire-opacity": 0.2 + intensity * 0.8,
      "--fire-blur": `${(1 - intensity) * 0.7}px`,
      "--fire-glow": `${7 + 22 * intensity}px`,
      "--fire-bottom": `${10 - 5 * intensity}%`,
      "--flame-one-width": `${20 + 28 * intensity}px`,
      "--flame-one-height": `${36 + 58 * intensity}px`,
      "--flame-two-width": `${15 + 21 * intensity}px`,
      "--flame-two-height": `${29 + 40 * intensity}px`,
      "--flame-three-width": `${14 + 18 * intensity}px`,
      "--flame-three-height": `${26 + 34 * intensity}px`,
      "--flame-scale": 0.62 + intensity * 0.38,
      "--flame-scale-x-start": 0.72 + intensity * 0.32,
      "--flame-scale-y-start": 0.76 + intensity * 0.32,
      "--flame-scale-x-end": 0.8 + intensity * 0.34,
      "--flame-scale-y-end": 0.84 + intensity * 0.4,
      "--ember-size": `${3 + 4 * intensity}px`,
      "--ember-opacity": 0.25 + 0.55 * intensity,
      "--ember-drift": `${-10 + 20 * intensity}px`,
    };

    return {
      ...goal,
      image: goal.status === "failed" ? burntMoneyTree : moneyTree,
      label: goal.status === "failed" ? `${goal.title} failed` : `${goal.title} money tree`,
      progress,
      intensity,
      fireStyle,
    };
  });
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
            forest.map((tree) => {
              const intensityPercent = Math.round(tree.intensity * 100);
              const progressPercent = Math.round(tree.progress * 100);

              return (
                <figure
                  key={tree.goalId || `${tree.title}-${tree.deadline}`}
                  className={`money-tree ${tree.status}`}
                  style={tree.fireStyle}
                  aria-label={`${tree.label}, ${progressPercent}% complete`}
                  title={`${tree.title}: ${progressPercent}% complete`}
                >
                  <div className="money-tree__stage">
                    <img className="money-tree__image" src={tree.image} alt="" />
                    {tree.status === "pending" ? (
                      <div className="money-tree__fire" aria-hidden="true">
                        <span className="flame flame-one" />
                        <span className="flame flame-two" />
                        <span className="flame flame-three" />
                        <span className="ember ember-one" />
                        <span className="ember ember-two" />
                      </div>
                    ) : null}
                  </div>
                  <figcaption>
                    {tree.status === "failed" ? "burnt" : `${intensityPercent}% fire`}
                  </figcaption>
                </figure>
              );
            })
          ) : (
            <p className="empty-state">Create a goal to plant the first money tree.</p>
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
