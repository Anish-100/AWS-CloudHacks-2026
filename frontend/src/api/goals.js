import { api } from "./client";

function normalizeGoals(payload) {
  if (Array.isArray(payload)) {
    return payload;
  }

  return payload?.goals || payload?.items || [];
}

export async function getGoals() {
  return normalizeGoals(await api("/goals"));
}

export async function createGoal(goal) {
  return api("/goals", {
    method: "POST",
    body: JSON.stringify(goal),
  });
}

export async function updateGoal(goalId, updates) {
  return api(`/goals/${goalId}`, {
    method: "PUT",
    body: JSON.stringify(updates),
  });
}

export async function deleteGoal(goalId) {
  return api(`/goals/${goalId}`, {
    method: "DELETE",
  });
}
