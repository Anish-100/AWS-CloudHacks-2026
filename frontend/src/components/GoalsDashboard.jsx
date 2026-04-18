import GoalCard from "./GoalCard.jsx";

export default function GoalsDashboard({ goals, onUpdateProgress, onDelete }) {
  const veryShortGoals = goals.filter((goal) => goal.type === "veryShort");
  const shortGoals = goals.filter((goal) => goal.type === "short");

  return (
    <section className="goals-dashboard">
      <div className="section-heading">
        <p className="eyebrow">Goals dashboard</p>
        <h2>Short wins, visible progress.</h2>
      </div>

      <div className="goal-group">
        <h3>This week</h3>
        {veryShortGoals.length ? (
          veryShortGoals.map((goal) => (
            <GoalCard
              key={goal.goalId}
              goal={goal}
              onUpdateProgress={onUpdateProgress}
              onDelete={onDelete}
            />
          ))
        ) : (
          <p className="empty-state">No 7-day goals yet.</p>
        )}
      </div>

      <div className="goal-group">
        <h3>Next three months</h3>
        {shortGoals.length ? (
          shortGoals.map((goal) => (
            <GoalCard
              key={goal.goalId}
              goal={goal}
              onUpdateProgress={onUpdateProgress}
              onDelete={onDelete}
            />
          ))
        ) : (
          <p className="empty-state">No short-term goals yet.</p>
        )}
      </div>
    </section>
  );
}
