export default function RecommendationsPanel({ recommendations, isLoading }) {
  const items = recommendations?.recommendations || [];
  const risks = recommendations?.riskCategories || [];

  return (
    <section className="recommendations-panel">
      <div className="section-heading">
        <p className="eyebrow">Bedrock advice</p>
        <h2>Small moves for this week.</h2>
      </div>

      {isLoading ? (
        <p className="empty-state">Checking spending patterns...</p>
      ) : (
        <>
          <ul className="recommendation-list">
            {items.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
          <div className="risk-row">
            {risks.map((risk) => (
              <span key={risk}>{risk}</span>
            ))}
          </div>
        </>
      )}
    </section>
  );
}
