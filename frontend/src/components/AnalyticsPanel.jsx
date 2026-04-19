import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const statusColors = {
  achieved: "#2ecc71",
  pending: "#e6b800",
  failed: "#ff6b2c",
};

function currency(value) {
  return `$${Number(value || 0).toLocaleString(undefined, {
    maximumFractionDigits: 0,
  })}`;
}

function getGoalValue(goal, key, fallbackKey) {
  return Number(goal[key] ?? goal[fallbackKey] ?? 0);
}

function normalizeRecommendationList(recommendations) {
  if (Array.isArray(recommendations?.suggestions)) {
    return recommendations.suggestions;
  }

  return [];
}

export default function AnalyticsPanel({ goals, recommendations }) {
  const goalProgress = goals.map((goal) => {
    const target = getGoalValue(goal, "targetAmount", "target_amount");
    const current = getGoalValue(goal, "currentAmount", "amount_saved");
    const remaining = Math.max(target - current, 0);

    return {
      name: goal.title || goal.description || "Goal",
      saved: current,
      remaining,
    };
  });

  const statusTotals = ["achieved", "pending", "failed"]
    .map((status) => ({
      name: status,
      value: goals.filter((goal) => goal.status === status).length,
    }))
    .filter((item) => item.value > 0);

  const suggestions = normalizeRecommendationList(recommendations);
  const savingsPotential = suggestions.reduce(
    (total, suggestion) => total + Number(suggestion.monthly_saving || 0),
    0,
  );

  return (
    <section className="analytics-panel">
      <div className="section-heading">
        <p className="eyebrow">Analytics</p>
        <h2>Goal health.</h2>
      </div>

      <div className="analytics-summary">
        <div>
          <span>Active goals</span>
          <strong>{goals.length}</strong>
        </div>
        <div>
          <span>Saved so far</span>
          <strong>
            {currency(
              goals.reduce(
                (total, goal) => total + getGoalValue(goal, "currentAmount", "amount_saved"),
                0,
              ),
            )}
          </strong>
        </div>
        <div>
          <span>Potential monthly lift</span>
          <strong>{currency(savingsPotential)}</strong>
        </div>
      </div>

      <div className="analytics-grid">
        <div className="chart-surface chart-surface-wide">
          <h3>Saved vs remaining</h3>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={goalProgress} margin={{ top: 8, right: 10, left: 0, bottom: 4 }}>
              <CartesianGrid stroke="rgba(202, 216, 207, 0.12)" vertical={false} />
              <XAxis dataKey="name" tick={{ fill: "#cad8cf", fontSize: 12 }} tickLine={false} />
              <YAxis tick={{ fill: "#a9b8ad", fontSize: 12 }} tickLine={false} width={44} tickFormatter={(v) => `$${v}`} />
              <Tooltip
                formatter={(value, name) => [currency(value), name === "saved" ? "Saved" : "Remaining"]}
                contentStyle={{ background: "#101412", border: "1px solid #304238", borderRadius: 8 }}
              />
              <Bar dataKey="saved" stackId="goal" fill="#2ecc71" radius={[0, 0, 0, 0]} name="saved" />
              <Bar dataKey="remaining" stackId="goal" fill="#e6b800" radius={[6, 6, 0, 0]} name="remaining" />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="chart-surface">
          <h3>Status mix</h3>
          <ResponsiveContainer width="100%" height={260}>
            <PieChart>
              <Pie data={statusTotals} dataKey="value" nameKey="name" outerRadius={86} label>
                {statusTotals.map((entry) => (
                  <Cell key={entry.name} fill={statusColors[entry.name]} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{ background: "#101412", border: "1px solid #304238", borderRadius: 8 }}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>
    </section>
  );
}
