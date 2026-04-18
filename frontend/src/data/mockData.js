export const mockGoals = [
  {
    goalId: "goal-1",
    title: "Save for next week's groceries",
    targetAmount: 140,
    currentAmount: 95,
    deadline: "2026-04-25",
    type: "veryShort",
    status: "pending",
  },
  {
    goalId: "goal-2",
    title: "Textbook fund",
    targetAmount: 260,
    currentAmount: 260,
    deadline: "2026-05-15",
    type: "short",
    status: "achieved",
  },
  {
    goalId: "goal-3",
    title: "Concert ticket",
    targetAmount: 90,
    currentAmount: 35,
    deadline: "2026-04-16",
    type: "veryShort",
    status: "failed",
  },
  {
    goalId: "goal-4",
    title: "Emergency cushion",
    targetAmount: 500,
    currentAmount: 210,
    deadline: "2026-06-30",
    type: "short",
    status: "pending",
  },
];

export const mockRecommendations = {
  recommendations: [
    "Move two restaurant meals to groceries this week to protect the grocery goal.",
    "Pause one entertainment purchase until the textbook fund clears.",
    "Put the next spare $25 toward the emergency cushion before adding a new goal.",
  ],
  riskCategories: ["Food & Drink", "Entertainment", "Gas"],
};
