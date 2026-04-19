import { useEffect, useMemo, useState } from "react";
import { hasApiBaseUrl } from "./api/client.js";
import { createGoal, deleteGoal, getGoals, updateGoal } from "./api/goals.js";
import { getRecommendations } from "./api/recommendations.js";
import { getUploadStatus, getUserData, requestUpload, uploadFinancialData, uploadToS3 } from "./api/upload.js";
import AnalyticsPanel from "./components/AnalyticsPanel.jsx";
import AppShell from "./components/AppShell.jsx";
import CsvUploader from "./components/CsvUploader.jsx";
import ForestCanvas from "./components/ForestCanvas.jsx";
import GoalForm from "./components/GoalForm.jsx";
import GoalsDashboard from "./components/GoalsDashboard.jsx";
import RecommendationsPanel from "./components/RecommendationsPanel.jsx";
import { mockGoals, mockRecommendations, mockTransactionData } from "./data/mockData.js";

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

export default function App() {
  const [goals, setGoals] = useState(() => mockGoals.map(normalizeGoalStatus));
  const [recommendations, setRecommendations] = useState(mockRecommendations);
  const [transactionData, setTransactionData] = useState(mockTransactionData);
  const [uploadStatus, setUploadStatus] = useState("Ready");
  const [isLoadingRecs, setIsLoadingRecs] = useState(false);
  const apiEnabled = hasApiBaseUrl();

  const apiMode = useMemo(() => (apiEnabled ? "API connected" : "Mock mode"), [apiEnabled]);

  useEffect(() => {
    if (!apiEnabled) {
      return;
    }

    getGoals()
      .then((loadedGoals) => {
        if (loadedGoals.length) {
          setGoals(loadedGoals.map(normalizeGoalStatus));
        }
      })
      .catch(() => setUploadStatus("API unavailable"));

    setIsLoadingRecs(true);
    getRecommendations()
      .then(setRecommendations)
      .catch(() => setRecommendations(mockRecommendations))
      .finally(() => setIsLoadingRecs(false));

    getUserData()
      .then(setTransactionData)
      .catch(() => console.error("Failed to load transaction data"));
  }, [apiEnabled]);

  async function handleCreateGoal(goal) {
    const nextGoal = withGeneratedGoalId({
      ...goal,
      status: deriveStatus(goal),
    });

    setGoals((current) => [nextGoal, ...current]);

    if (apiEnabled) {
      try {
        const savedGoal = await createGoal(goal);
        if (savedGoal) {
          setGoals((current) =>
            current.map((item) => (item.goalId === nextGoal.goalId ? withGeneratedGoalId(savedGoal) : item)),
          );
        }
      } catch {
        setUploadStatus("Goal saved locally");
      }
    }
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

    if (apiEnabled) {
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

      getUserData()
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
          <RecommendationsPanel recommendations={recommendations} isLoading={isLoadingRecs} />
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