import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
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

function computeMonthlySpending(transactions) {
  const totals = {};
  for (const tx of transactions) {
    if (tx.amount >= 0) continue;
    const month = tx.date?.slice(0, 7);
    if (!month) continue;
    totals[month] = (totals[month] || 0) + Math.abs(tx.amount);
  }
  return Object.entries(totals)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([month, spent]) => ({ month, spent: Math.round(spent * 100) / 100 }));
}

function computeCategoryInsights(transactions) {
  if (!transactions || transactions.length === 0) return [];

  // Group spending by month and category
  const byMonthCategory = {};
  for (const tx of transactions) {
    if (tx.amount >= 0) continue;
    const month = tx.date?.slice(0, 7);
    const category = tx.category || "Other";
    if (!month || !category) continue;
    if (!byMonthCategory[month]) byMonthCategory[month] = {};
    byMonthCategory[month][category] = (byMonthCategory[month][category] || 0) + Math.abs(tx.amount);
  }

  const months = Object.keys(byMonthCategory).sort();
  if (months.length < 2) return []; // need at least 2 months to compare

  const currentMonth = months[months.length - 1];
  const pastMonths = months.slice(0, -1);

  // Get all categories in current month
  const currentCategories = byMonthCategory[currentMonth] || {};

  // Compute average for each category across past months
  const insights = Object.entries(currentCategories)
    .map(([category, currentSpent]) => {
      const pastTotals = pastMonths.map((m) => byMonthCategory[m]?.[category] || 0);
      const avg = pastTotals.reduce((a, b) => a + b, 0) / pastMonths.length;
      const diff = currentSpent - avg;
      const pct = avg > 0 ? Math.round((diff / avg) * 100) : 0;

      return { category, currentSpent, avg, diff, pct };
    })
    .sort((a, b) => Math.abs(b.pct) - Math.abs(a.pct)) // sort by biggest change
    .slice(0, 3); // top 3

  return insights;
}

function CompletionLabel(props) {
  const { x, y, width, value, index, data } = props;
  if (data[index]?.remaining !== 0) return null;
  return (
    <text
      x={x + width / 2}
      y={y - 8}
      fill="#2ecc71"
      textAnchor="middle"
      fontSize={18}
      fontWeight="bold"
    >
      ✓
    </text>
  );
}

export default function AnalyticsPanel({ goals, recommendations, transactionData }) {
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

  const monthlySpending = computeMonthlySpending(transactionData?.transactions || []);
  const categoryInsights = computeCategoryInsights(transactionData?.transactions || []);

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
        {/* Saved vs Remaining */}
        <div className="chart-surface chart-surface-wide">
          <h3>Saved vs remaining</h3>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart
              data={goalProgress}
              margin={{ top: 8, right: 10, left: 0, bottom: 60 }}
            >
              <CartesianGrid stroke="rgba(202, 216, 207, 0.12)" vertical={false} />
              <XAxis
                dataKey="name"
                tick={{ fill: "#cad8cf", fontSize: 12 }}
                tickLine={false}
                angle={-35}
                textAnchor="end"
                interval={0}
              />
              <YAxis
                tick={{ fill: "#a9b8ad", fontSize: 12 }}
                tickLine={false}
                width={54}
                tickFormatter={(v) => `$${v}`}
              />
              <Tooltip
                formatter={(value, name) => [currency(value), name === "saved" ? "Saved" : "Remaining"]}
                contentStyle={{ background: "#101412", border: "1px solid #304238", borderRadius: 8 }}
              />
              <Bar dataKey="saved" stackId="goal" fill="#2ecc71" radius={[0, 0, 0, 0]} name="saved"
              label={<CompletionLabel data={goalProgress} />}
              />
              <Bar dataKey="remaining" stackId="goal" fill="#e6b800" radius={[6, 6, 0, 0]} name="remaining" />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Status Mix */}
        <div className="chart-surface">
          <h3>Status mix</h3>
          <ResponsiveContainer width="100%" height={280}>
            <PieChart>
              <Pie
                data={statusTotals}
                dataKey="value"
                nameKey="name"
                outerRadius={75}
              >
                {statusTotals.map((entry) => (
                  <Cell key={entry.name} fill={statusColors[entry.name]} />
                ))}
              </Pie>
              <Tooltip
                formatter={(value, name) => [value, name]}
                contentStyle={{ background: "#101412", border: "1px solid #304238", borderRadius: 8 }}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Monthly Spending Trend */}
        <div className="chart-surface chart-surface-wide">
          <h3>Monthly spending trend</h3>
          {monthlySpending.length === 0 ? (
            <p style={{ color: "#a9b8ad", fontSize: 13, marginTop: 12 }}>No transaction data available.</p>
          ) : (
            <ResponsiveContainer width="100%" height={280}>
              <LineChart
                data={monthlySpending}
                margin={{ top: 8, right: 10, left: 0, bottom: 4 }}
              >
                <CartesianGrid stroke="rgba(202, 216, 207, 0.12)" vertical={false} />
                <XAxis
                  dataKey="month"
                  tick={{ fill: "#cad8cf", fontSize: 12 }}
                  tickLine={false}
                />
                <YAxis
                  tick={{ fill: "#a9b8ad", fontSize: 12 }}
                  tickLine={false}
                  width={54}
                  tickFormatter={(v) => `$${v}`}
                />
                <Tooltip
                  formatter={(value) => [currency(value), "Spent"]}
                  contentStyle={{ background: "#101412", border: "1px solid #304238", borderRadius: 8 }}
                />
                <Line
                  type="monotone"
                  dataKey="spent"
                  stroke="#ff6b2c"
                  strokeWidth={2}
                  dot={{ fill: "#ff6b2c", r: 4 }}
                  activeDot={{ r: 6 }}
                />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Category Insights */}
        <div className="chart-surface chart-surface-wide">
          <h3>Your spending vs your average</h3>
          {categoryInsights.length === 0 ? (
            <p style={{ color: "#a9b8ad", fontSize: 13, marginTop: 12 }}>Need at least 2 months of data to compare.</p>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 16, marginTop: 12 }}>
              {categoryInsights.map(({ category, currentSpent, avg, pct }) => {
                const better = pct <= 0;
                const color = better ? "#2ecc71" : "#ff6b2c";
                const arrow = better ? "▼" : "▲";
                const label = better
                  ? `${Math.abs(pct)}% personal avg`
                  : `${Math.abs(pct)}% personal avg`;

                return (
                  <div key={category} style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <span style={{ color: "#cad8cf", fontSize: 14, fontWeight: 600 }}>{category}</span>
                      <span style={{ color, fontSize: 13, fontWeight: 600 }}>{arrow} {label}</span>
                    </div>
                    <div style={{ display: "flex", justifyContent: "space-between" }}>
                      <span style={{ color: "#a9b8ad", fontSize: 12 }}>This month: <strong style={{ color: "#cad8cf" }}>{currency(currentSpent)}</strong></span>
                      <span style={{ color: "#a9b8ad", fontSize: 12 }}>Your avg: <strong style={{ color: "#cad8cf" }}>{currency(avg)}</strong></span>
                    </div>
                    {/* Progress bar */}
                    <div style={{ background: "#1e2e28", borderRadius: 4, height: 6, overflow: "hidden" }}>
                      <div style={{
                        width: `${Math.min((currentSpent / (avg * 1.5)) * 100, 100)}%`,
                        background: color,
                        height: "100%",
                        borderRadius: 4,
                        transition: "width 0.4s ease",
                      }} />
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </section>
  );
}