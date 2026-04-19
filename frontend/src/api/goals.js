import { api } from "./client";

const DATASET_ID = import.meta.env.VITE_DATASET_ID || import.meta.env.VITE_USER_ID || "demo";

function withDataset(path) {
  const params = new URLSearchParams({ dataset_id: DATASET_ID });
  return `${path}?${params.toString()}`;
}

function normalizeGoal(goal) {
  if (!goal) {
    return goal;
  }

  const targetAmount = goal.targetAmount ?? goal.target_amount ?? goal.TotalAmount ?? 0;
  const currentAmount = goal.currentAmount ?? goal.amount_saved ?? goal.AmountSaved ?? 0;
  const deadline = goal.deadline ?? goal.end_date ?? goal.EndDate ?? "";
  const title = goal.title ?? goal.description ?? goal.Description ?? "Untitled goal";
  const type = goal.type ?? goal.category ?? goal.Category ?? "short";
  const result = goal.result ?? goal.Result;

  return {
    ...goal,
    goalId: goal.goalId ?? goal.goal_id ?? goal.SK?.replace("GOAL#", ""),
    title,
    targetAmount: Number(targetAmount),
    currentAmount: Number(currentAmount),
    deadline,
    type,
    status: goal.status ?? (result ? "achieved" : "pending"),
  };
}

function normalizeGoals(payload) {
  const goals = Array.isArray(payload) ? payload : payload?.goals || payload?.items || [];

  return goals.map(normalizeGoal);
}

export async function getGoals() {
  return normalizeGoals(await api(withDataset("/goals")));
}

export async function createGoal(goal) {
  return normalizeGoal(await api("/goals", {
    method: "POST",
    body: JSON.stringify({
      dataset_id: goal.dataset_id || DATASET_ID,
      ...goal,
    }),
  }));
}

export async function updateGoal(goalId, updates) {
  return api(`/goals/${goalId}`, {
    method: "PUT",
    body: JSON.stringify({
      dataset_id: updates.dataset_id || DATASET_ID,
      ...updates,
    }),
  });
}

export async function deleteGoal(goalId) {
  return api(withDataset(`/goals/${goalId}`), {
    method: "DELETE",
  });
}
