import StatusBadge from "./StatusBadge.jsx";

function formatCurrency(value) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(Number(value || 0));
}

export default function GoalCard({ goal, onUpdateProgress, onDelete }) {
  const target = Number(goal.targetAmount || 0);
  const current = Number(goal.currentAmount || 0);
  const progress = target > 0 ? Math.min((current / target) * 100, 100) : 0;

  return (
    <article className="goal-card">
      <div className="goal-card__header">
        <div>
          <p className="eyebrow">{goal.type === "veryShort" ? "7-day goal" : "Short-term goal"}</p>
          <h3>{goal.title}</h3>
        </div>
        <StatusBadge status={goal.status} />
      </div>

      <div className="progress-row">
        <span>{formatCurrency(current)}</span>
        <span>{formatCurrency(target)}</span>
      </div>
      <div className="progress-track" aria-label={`${Math.round(progress)}% complete`}>
        <div className="progress-fill" style={{ width: `${progress}%` }} />
      </div>

      <div className="goal-card__footer">
        <span>Due {goal.deadline}</span>
        <div className="button-row">
          <button type="button" onClick={() => onUpdateProgress(goal)}>
            Add progress
          </button>
          <button type="button" className="ghost danger" onClick={() => onDelete(goal.goalId)}>
            Delete
          </button>
        </div>
      </div>
    </article>
  );
}
