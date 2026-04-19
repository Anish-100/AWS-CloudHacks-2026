function normalizeRecommendation(item, index) {
  if (typeof item === "string") {
    return {
      suggestion_id: item,
      action: item,
      monthly_saving: 0,
      taken: false,
    };
  }

  return {
    suggestion_id: item.suggestion_id || item.id || item.action || `suggestion-${index}`,
    action: item.action || item.text || "",
    category: item.category || "",
    monthly_saving: Number(item.monthly_saving || item.monthlySaving || 0),
    taken: Boolean(item.taken),
  };
}

export default function RecommendationsPanel({
  recommendations,
  isLoading,
  acceptedAdvice = [],
  rejectedAdvice = [],
  onAcceptAdvice,
  onRejectAdvice,
}) {
  const sourceItems = recommendations?.suggestions || recommendations?.recommendations || [];
  const items = sourceItems.map(normalizeRecommendation);
  const risks = recommendations?.riskCategories || [];
  const acceptedSet = new Set(acceptedAdvice);
  const rejectedSet = new Set(rejectedAdvice);

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
            {items.map((item) => {
              const isAccepted = item.taken || acceptedSet.has(item.suggestion_id);
              const isRejected = rejectedSet.has(item.suggestion_id);
              const isSettled = isAccepted || isRejected;

              return (
                <li key={item.suggestion_id}>
                  <div className="recommendation-choice">
                    <label className={isAccepted ? "accepted" : isRejected ? "rejected" : ""}>
                      <input
                        type="checkbox"
                        checked={isAccepted}
                        disabled={isSettled}
                        onChange={() => onAcceptAdvice?.(item)}
                      />
                      <span className="recommendation-status" aria-hidden="true" />
                      <span>
                        {item.action}
                        {item.monthly_saving > 0 ? (
                          <strong> Save ${item.monthly_saving.toFixed(0)}</strong>
                        ) : null}
                      </span>
                    </label>
                    <button
                      type="button"
                      className="ghost recommendation-reject"
                      disabled={isSettled}
                      onClick={() => onRejectAdvice?.(item)}
                    >
                      Reject
                    </button>
                  </div>
                </li>
              );
            })}
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
