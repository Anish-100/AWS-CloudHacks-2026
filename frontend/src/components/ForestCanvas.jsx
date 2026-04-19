import { useMemo } from "react";

import moneyTree from "../Images/tree-icon-in-pixel-art-png.png";
import burntMoneyTree from "../Images/burntTree.png";

const FOREST_POSITION_STORAGE_KEY = "puran.forest.positions.v1";
const POSITION_ATTEMPTS = 90;
const MIN_TREE_SPACING_X = 17;
const MIN_TREE_SPACING_Y = 24;
const FIELD_MIN_X = 11;
const FIELD_MAX_X = 89;
const FIELD_MIN_Y = 15;
const FIELD_MAX_Y = 83;

function getGoalKey(goal, index) {
  return goal.goalId || `${goal.title || "goal"}-${goal.deadline || index}`;
}

function hashString(value) {
  return [...String(value)].reduce((hash, char) => {
    return (hash * 31 + char.charCodeAt(0)) >>> 0;
  }, 2166136261);
}

function createRandom(seed) {
  let state = hashString(seed) || 1;

  return () => {
    state = (state * 1664525 + 1013904223) >>> 0;
    return state / 4294967296;
  };
}

function readStoredPositions() {
  if (typeof window === "undefined") {
    return {};
  }

  try {
    return JSON.parse(window.localStorage.getItem(FOREST_POSITION_STORAGE_KEY)) || {};
  } catch {
    return {};
  }
}

function writeStoredPositions(positions) {
  if (typeof window === "undefined") {
    return;
  }

  try {
    window.localStorage.setItem(FOREST_POSITION_STORAGE_KEY, JSON.stringify(positions));
  } catch {
    // The board can still render with in-memory positions if storage is unavailable.
  }
}

function isOpenPosition(position, occupied) {
  return occupied.every((item) => {
    const xGap = Math.abs(position.x - item.x);
    const yGap = Math.abs(position.y - item.y);

    return xGap >= MIN_TREE_SPACING_X || yGap >= MIN_TREE_SPACING_Y;
  });
}

function isOnField(position) {
  return (
    position.x >= FIELD_MIN_X &&
    position.x <= FIELD_MAX_X &&
    position.y >= FIELD_MIN_Y &&
    position.y <= FIELD_MAX_Y
  );
}

function createTreePosition(goalKey, occupied) {
  const random = createRandom(goalKey);
  let bestPosition = null;
  let bestScore = -1;

  for (let attempt = 0; attempt < POSITION_ATTEMPTS; attempt += 1) {
    const position = {
      x: FIELD_MIN_X + random() * (FIELD_MAX_X - FIELD_MIN_X),
      y: FIELD_MIN_Y + random() * (FIELD_MAX_Y - FIELD_MIN_Y),
    };

    if (!isOnField(position)) {
      continue;
    }

    if (isOpenPosition(position, occupied)) {
      return position;
    }

    const nearestNeighbor = occupied.reduce((nearest, item) => {
      const xGap = Math.abs(position.x - item.x) / MIN_TREE_SPACING_X;
      const yGap = Math.abs(position.y - item.y) / MIN_TREE_SPACING_Y;
      return Math.min(nearest, Math.hypot(xGap, yGap));
    }, Number.POSITIVE_INFINITY);

    if (nearestNeighbor > bestScore) {
      bestScore = nearestNeighbor;
      bestPosition = position;
    }
  }

  return bestPosition || { x: 50, y: 52 };
}

function getForestPositions(goals) {
  const storedPositions = readStoredPositions();
  const nextPositions = {};
  const occupied = [];

  goals.forEach((goal, index) => {
    const goalKey = getGoalKey(goal, index);
    const storedPosition = storedPositions[goalKey];

    if (storedPosition && isOnField(storedPosition) && isOpenPosition(storedPosition, occupied)) {
      occupied.push(storedPosition);
      nextPositions[goalKey] = storedPosition;
    }
  });

  goals.forEach((goal, index) => {
    const goalKey = getGoalKey(goal, index);

    if (nextPositions[goalKey]) {
      return;
    }

    const position = createTreePosition(goalKey, occupied);
    occupied.push(position);
    nextPositions[goalKey] = position;
  });

  writeStoredPositions(nextPositions);

  return nextPositions;
}

function getGoalProgress(goal) {
  const target = Number(goal.targetAmount || 0);
  const current = Number(goal.currentAmount || 0);

  if (target <= 0) {
    return 0;
  }

  return Math.min(Math.max(current / target, 0), 1);
}

function buildForest(goals, positions) {
  return goals.map((goal, index) => {
    const goalKey = getGoalKey(goal, index);
    const progress = getGoalProgress(goal);
    const intensity = goal.status === "pending" ? Math.max(0.12, 1 - progress) : 0;
    const fireStyle = {
      "--tree-x": `${positions[goalKey]?.x ?? 50}%`,
      "--tree-y": `${positions[goalKey]?.y ?? 50}%`,
      "--fire-intensity": intensity,
      "--fire-opacity": 0.2 + intensity * 0.8,
      "--fire-blur": `${(1 - intensity) * 0.7}px`,
      "--fire-glow": `${7 + 22 * intensity}px`,
      "--fire-bottom": `${2 - 2 * intensity}%`,
      "--flame-one-width": `${20 + 28 * intensity}px`,
      "--flame-one-height": `${36 + 58 * intensity}px`,
      "--flame-two-width": `${15 + 21 * intensity}px`,
      "--flame-two-height": `${29 + 40 * intensity}px`,
      "--flame-three-width": `${14 + 18 * intensity}px`,
      "--flame-three-height": `${26 + 34 * intensity}px`,
      "--flame-scale": 0.62 + intensity * 0.38,
      "--flame-scale-x-start": 0.72 + intensity * 0.32,
      "--flame-scale-y-start": 0.76 + intensity * 0.32,
      "--flame-scale-x-end": 0.8 + intensity * 0.34,
      "--flame-scale-y-end": 0.84 + intensity * 0.4,
      "--ember-size": `${3 + 4 * intensity}px`,
      "--ember-opacity": 0.25 + 0.55 * intensity,
      "--ember-drift": `${-10 + 20 * intensity}px`,
    };

    return {
      ...goal,
      image: goal.status === "failed" ? burntMoneyTree : moneyTree,
      goalKey,
      label: goal.status === "failed" ? `${goal.title} failed` : `${goal.title} money tree`,
      progress,
      intensity,
      fireStyle,
    };
  });
}

export default function ForestCanvas({ goals }) {
  const positions = useMemo(() => getForestPositions(goals), [goals]);
  const forest = buildForest(goals, positions);
  const achieved = goals.filter((goal) => goal.status === "achieved").length;
  const pending = goals.filter((goal) => goal.status === "pending").length;
  const failed = goals.filter((goal) => goal.status === "failed").length;

  return (
    <section className="forest-panel">
      <div className="forest-image" aria-hidden="true">
        <span className="pixel-island" />
      </div>
      <div className="forest-content">
        <div className="section-heading">
          <p className="eyebrow">Goal forest</p>
          <h2>Your habits grow here.</h2>
        </div>

        <div className="forest-ground" aria-label="Goal forest status">
          {forest.length ? (
            forest.map((tree) => {
              const intensityPercent = Math.round(tree.intensity * 100);
              const progressPercent = Math.round(tree.progress * 100);

              return (
                <figure
                  key={tree.goalKey}
                  className={`money-tree ${tree.status}`}
                  style={tree.fireStyle}
                  aria-label={`${tree.label}, ${progressPercent}% complete`}
                  title={`${tree.title}: ${progressPercent}% complete`}
                >
                  <div className="money-tree__stage">
                    <img className="money-tree__image" src={tree.image} alt="" />
                    {tree.status === "pending" ? (
                      <div className="money-tree__fire" aria-hidden="true">
                        <span className="flame flame-one" />
                        <span className="flame flame-two" />
                        <span className="flame flame-three" />
                        <span className="ember ember-one" />
                        <span className="ember ember-two" />
                      </div>
                    ) : null}
                  </div>
                  <figcaption>
                    {tree.status === "failed" ? "burnt" : `${intensityPercent}% fire`}
                  </figcaption>
                </figure>
              );
            })
          ) : (
            <p className="empty-state">Create a goal to plant the first money tree.</p>
          )}
        </div>

        <div className="forest-stats">
          <span>{achieved} achieved</span>
          <span>{pending} active</span>
          <span>{failed} failed</span>
        </div>
      </div>
    </section>
  );
}
