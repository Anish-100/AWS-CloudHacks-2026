import { api } from "./client";

const DATASET_ID = import.meta.env.VITE_DATASET_ID || import.meta.env.VITE_USER_ID || "demo";

function withDataset(path) {
  const params = new URLSearchParams({ dataset_id: DATASET_ID });
  return `${path}?${params.toString()}`;
}

export async function getRecommendations() {
  return api(withDataset("/suggestions"));
}

export async function generateRecommendations() {
  return api(withDataset("/suggestions/generate"));
}

export async function acceptRecommendation(recommendation) {
  return api("/suggestions", {
    method: "POST",
    body: JSON.stringify({
      dataset_id: DATASET_ID,
      suggestion_id: recommendation.suggestion_id || recommendation.id || recommendation.action,
      accepted: true,
      category: recommendation.category || "",
      action: recommendation.action || recommendation.text || recommendation,
      monthly_saving: recommendation.monthly_saving || recommendation.monthlySaving || 0,
      apply_to_nearest_goal: false,
      generate_replacement: false,
    }),
  });
}

export async function rejectRecommendation(recommendation) {
  return api("/suggestions", {
    method: "POST",
    body: JSON.stringify({
      dataset_id: DATASET_ID,
      suggestion_id: recommendation.suggestion_id || recommendation.id || recommendation.action,
      accepted: false,
      category: recommendation.category || "",
      action: recommendation.action || recommendation.text || recommendation,
      monthly_saving: recommendation.monthly_saving || recommendation.monthlySaving || 0,
      generate_replacement: false,
    }),
  });
}
