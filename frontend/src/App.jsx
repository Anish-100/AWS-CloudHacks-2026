import { useEffect, useMemo, useState } from "react";
import { hasApiBaseUrl } from "./api/client.js";
import { getFinancialData } from "./api/financialData.js";
import { createGoal, deleteGoal, getGoals, updateGoal } from "./api/goals.js";
import {
  acceptRecommendation,
  generateRecommendations,
  getRecommendations,
  rejectRecommendation,
} from "./api/recommendations.js";
import { getUploadStatus, requestUpload, uploadToS3 } from "./api/upload.js";
import AnalyticsPanel from "./components/AnalyticsPanel.jsx";
import AppShell from "./components/AppShell.jsx";
import CsvUploader from "./components/CsvUploader.jsx";
import ForestCanvas from "./components/ForestCanvas.jsx";
import GoalForm from "./components/GoalForm.jsx";
import GoalsDashboard from "./components/GoalsDashboard.jsx";
import RecommendationsPanel from "./components/RecommendationsPanel.jsx";
import { mockRecommendations, mockTransactionData } from "./data/mockData.js";

const GOAL_REFRESH_DELAY_MS = 1500;

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function withGeneratedGoalId(goal) {
  return {
    ...goal,
    goalId: goal.goalId || crypto.randomUUID(),
  };
}

function isPastDeadline(deadline) {
  if (!deadline) {
    return false;
  }

  const deadlineEnd = new Date(`${deadline}T23:59:59`);
  return !Number.isNaN(deadlineEnd.getTime()) && deadlineEnd < new Date();
}

function deriveStatus(goal) {
  if (goal.status === "achieved") {
    return goal.status;
  }

  if (Number(goal.currentAmount) >= Number(goal.targetAmount)) {
    return "achieved";
  }

  if (goal.status === "failed" || isPastDeadline(goal.deadline)) {
    return "failed";
  }

  return "pending";
}

function normalizeGoalStatus(goal) {
  return {
    ...goal,
    status: deriveStatus(goal),
  };
}

function getGoalValue(goal, camelKey, snakeKey, fallback = "") {
  return goal[camelKey] ?? goal[snakeKey] ?? fallback;
}

function getGoalId(goal) {
  return getGoalValue(goal, "goalId", "goal_id") || goal.SK?.replace("GOAL#", "");
}

function getGoalDeadline(goal) {
  return getGoalValue(goal, "deadline", "end_date");
}

function getGoalCurrent(goal) {
  return Number(getGoalValue(goal, "currentAmount", "amount_saved", 0));
}

function getGoalTarget(goal) {
  return Number(getGoalValue(goal, "targetAmount", "target_amount", 0));
}

function findNearestActiveGoal(goals) {
  return [...goals]
    .filter((goal) => {
      const status = goal.status || (goal.result ? "achieved" : "pending");
      return status === "pending" && getGoalCurrent(goal) < getGoalTarget(goal);
    })
    .sort((a, b) => new Date(getGoalDeadline(a) || "9999-12-31") - new Date(getGoalDeadline(b) || "9999-12-31"))[0];
}

function applySavingsToGoal(goal, savings) {
  const currentAmount = Math.min(getGoalCurrent(goal) + savings, getGoalTarget(goal));
  const updates = {
    currentAmount,
    amount_saved: currentAmount,
    status: deriveStatus({ ...goal, currentAmount }),
  };

  return {
    ...goal,
    ...updates,
  };
}

export default function App() {
  const apiEnabled = hasApiBaseUrl();
  const [goals, setGoals] = useState([]);
  const [recommendations, setRecommendations] = useState(mockRecommendations);
  const [transactionData, setTransactionData] = useState(() => (apiEnabled ? { transactions: [] } : mockTransactionData));
  const [uploadStatus, setUploadStatus] = useState("Ready");
  const [isLoadingRecs, setIsLoadingRecs] = useState(false);
  const [acceptedAdvice, setAcceptedAdvice] = useState([]);
  const [rejectedAdvice, setRejectedAdvice] = useState([]);

  const apiMode = useMemo(() => (apiEnabled ? "API connected" : "Mock mode"), [apiEnabled]);

  async function refreshGoals() {
    const loadedGoals = await getGoals();
    setGoals(loadedGoals.map(normalizeGoalStatus));
  }

  async function refreshGeneratedRecommendations() {
    try {
      const nextRecommendations = await generateRecommendations();
      setRecommendations(nextRecommendations);
      setAcceptedAdvice([]);
      setRejectedAdvice([]);
    } catch (error) {
      console.error("Failed to generate suggestions", error);
      setRecommendations(await getRecommendations());
    }
  }

  useEffect(() => {
    if (!apiEnabled) {
      return;
    }

    refreshGoals().catch(() => setUploadStatus("API unavailable"));

    setIsLoadingRecs(true);
    refreshGeneratedRecommendations()
      .catch(() => setRecommendations(mockRecommendations))
      .finally(() => setIsLoadingRecs(false));

    getFinancialData()
      .then(setTransactionData)
      .catch(() => console.error("Failed to load transaction data"));
  }, [apiEnabled]);

  async function handleCreateGoal(goal) {
    const nextGoal = withGeneratedGoalId({
      ...goal,
      status: deriveStatus(goal),
    });

    if (apiEnabled) {
      try {
        setUploadStatus("Saving goal");
        await createGoal(goal);
        await delay(GOAL_REFRESH_DELAY_MS);
        await refreshGoals();
        setUploadStatus("Goal saved");
      } catch {
        setGoals((current) => [nextGoal, ...current]);
        setUploadStatus("Goal saved locally");
      }

      return;
    }

    setGoals((current) => [nextGoal, ...current]);
  }

  async function handleUpdateProgress(goal) {
    const amount = window.prompt("How much have you saved now?", goal.currentAmount);
    if (amount === null) {
      return;
    }

    const currentAmount = Number(amount);
    if (Number.isNaN(currentAmount) || currentAmount < 0) {
      return;
    }

    const updates = {
      currentAmount,
      status: deriveStatus({ ...goal, currentAmount }),
    };

    setGoals((current) =>
      current.map((item) => (item.goalId === goal.goalId ? { ...item, ...updates } : item)),
    );

    if (apiEnabled && goal.goalId) {
      try {
        await updateGoal(goal.goalId, updates);
      } catch {
        setUploadStatus("Progress saved locally");
      }
    }
  }

  async function handleDeleteGoal(goalId) {
    setGoals((current) => current.filter((goal) => goal.goalId !== goalId));

    if (apiEnabled) {
      try {
        await deleteGoal(goalId);
      } catch {
        setUploadStatus("Goal deleted locally");
      }
    }
  }

  async function handleAcceptAdvice(recommendation) {
    const suggestionId = recommendation.suggestion_id || recommendation.action;
    const savings = Number(recommendation.monthly_saving || 0);
    const nearestGoal = findNearestActiveGoal(goals);
    const nearestGoalId = nearestGoal ? getGoalId(nearestGoal) : null;
    const updatedGoal = nearestGoal && savings > 0 ? applySavingsToGoal(nearestGoal, savings) : null;

    setAcceptedAdvice((current) => [...new Set([...current, suggestionId])]);

    if (updatedGoal && nearestGoalId) {
      setGoals((current) => current.map((goal) => (getGoalId(goal) === nearestGoalId ? updatedGoal : goal)));
    }

    if (!apiEnabled) {
      setUploadStatus(nearestGoal && savings > 0 ? "Advice accepted: nearest goal updated" : "Advice accepted");
      return;
    }

    try {
      if (updatedGoal && nearestGoalId) {
        await updateGoal(nearestGoalId, {
          currentAmount: updatedGoal.currentAmount,
          status: updatedGoal.status,
        });
      }

      const response = await acceptRecommendation(recommendation);
      const serverGoal = response?.updatedGoal;

      if (serverGoal?.goalId) {
        setGoals((current) =>
          current.map((goal) =>
            getGoalId(goal) === serverGoal.goalId
              ? normalizeGoalStatus({
                  ...goal,
                  ...serverGoal,
                })
              : goal,
          ),
        );
      }

      refreshGeneratedRecommendations().catch(() => console.error("Failed to refresh generated suggestions"));

      setUploadStatus("Advice accepted");
    } catch {
      setUploadStatus("Advice accepted locally");
    }
  }

  async function handleRejectAdvice(recommendation) {
    const suggestionId = recommendation.suggestion_id || recommendation.action;
    setRejectedAdvice((current) => [...new Set([...current, suggestionId])]);

    if (!apiEnabled) {
      setUploadStatus("Advice rejected");
      return;
    }

    try {
      await rejectRecommendation(recommendation);
      refreshGeneratedRecommendations().catch(() => console.error("Failed to refresh generated suggestions"));
      setUploadStatus("Advice rejected");
    } catch {
      setUploadStatus("Could not reject advice");
    }
  }

  async function pollStatus(batchId) {
    if (!batchId) {
      setUploadStatus("Processing");
      return;
    }

    for (let attempt = 0; attempt < 12; attempt += 1) {
      const status = await getUploadStatus(batchId);
      const state = status?.status || status?.state || "processing";
      setUploadStatus(state);

      if (["complete", "completed", "failed", "error"].includes(state.toLowerCase())) {
        return;
      }

      await new Promise((resolve) => setTimeout(resolve, 3000));
    }
  }

  async function handleUpload(file) {
    if (!apiEnabled) {
      setUploadStatus(`Demo loaded: ${file.name}`);
      return;
    }

    try {
      setUploadStatus("Requesting upload URL");
      const upload = await requestUpload(file);
      const uploadUrl = upload?.uploadUrl || upload?.url;
      const batchId = upload?.batchId || upload?.batch_id;

      if (!uploadUrl) {
        throw new Error("Upload URL missing");
      }

      setUploadStatus("Uploading to S3");
      await uploadToS3(uploadUrl, file);
      setUploadStatus("Processing");
      await new Promise((resolve) => setTimeout(resolve, 5000));

      const datasetId = upload?.datasetId || upload?.dataset_id || upload?.key?.split("/")[1];
      getFinancialData(datasetId)
        .then(setTransactionData)
        .catch(() => console.error("Failed to refresh transaction data"));

      setUploadStatus("Upload complete");
    } catch (error) {
      setUploadStatus(`Upload failed: ${error.message}`);
    }
  }

  return (
    <AppShell apiMode={apiMode} uploadStatus={uploadStatus}>
      <main className="dashboard-grid">
        <div className="left-rail">
          <CsvUploader onUpload={handleUpload} />
          <RecommendationsPanel
            recommendations={recommendations}
            isLoading={isLoadingRecs}
            acceptedAdvice={acceptedAdvice}
            rejectedAdvice={rejectedAdvice}
            onAcceptAdvice={handleAcceptAdvice}
            onRejectAdvice={handleRejectAdvice}
          />
        </div>

        <div className="center-stage">
          <ForestCanvas goals={goals} />
          <AnalyticsPanel goals={goals} recommendations={recommendations} transactionData={transactionData} />
        </div>

        <aside className="right-rail">
          <GoalForm onCreate={handleCreateGoal} />
          <GoalsDashboard goals={goals} onUpdateProgress={handleUpdateProgress} onDelete={handleDeleteGoal} />
        </aside>
      </main>
    </AppShell>
  );
}
