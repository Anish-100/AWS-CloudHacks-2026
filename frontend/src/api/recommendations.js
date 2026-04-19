import { api } from "./client";

export async function getRecommendations() {
  return api("/suggestions");
}

export async function acceptRecommendation(recommendation) {
  return api("/suggestions", {
    method: "POST",
    body: JSON.stringify({
      suggestion_id: recommendation.suggestion_id || recommendation.id || recommendation.action,
      accepted: true,
      category: recommendation.category || "",
      action: recommendation.action || recommendation.text || recommendation,
      monthly_saving: recommendation.monthly_saving || recommendation.monthlySaving || 0,
      apply_to_nearest_goal: true,
    }),
  });
}

export async function rejectRecommendation(recommendation) {
  return api("/suggestions", {
    method: "POST",
    body: JSON.stringify({
      suggestion_id: recommendation.suggestion_id || recommendation.id || recommendation.action,
      accepted: false,
      category: recommendation.category || "",
      action: recommendation.action || recommendation.text || recommendation,
      monthly_saving: recommendation.monthly_saving || recommendation.monthlySaving || 0,
      generate_replacement: true,
    }),
  });
}
