import { api } from "./client";

const DATASET_ID = import.meta.env.VITE_DATASET_ID || import.meta.env.VITE_USER_ID || "demo";

function normalizeDate(value) {
  if (!value) {
    return "";
  }

  const text = String(value);
  if (/^\d{4}-\d{2}-\d{2}$/.test(text)) {
    return text;
  }

  const parsed = new Date(text);
  if (Number.isNaN(parsed.getTime())) {
    return text;
  }

  return parsed.toISOString().slice(0, 10);
}

function normalizeTransaction(transaction) {
  const amount = Number(transaction.amount ?? transaction.Amount ?? 0);

  return {
    ...transaction,
    date: normalizeDate(transaction.date ?? transaction.TransactionDate),
    description: transaction.description ?? transaction.Description ?? "",
    category: transaction.category ?? transaction.Category ?? "Other",
    type: transaction.type ?? transaction.Type ?? "",
    amount,
    specs: transaction.specs ?? transaction.Specs ?? "",
  };
}

export function normalizeFinancialData(payload) {
  const transactions = Array.isArray(payload?.transactions) ? payload.transactions : [];

  return {
    ...payload,
    datasetId: payload?.datasetId ?? payload?.dataset_id ?? DATASET_ID,
    transactions: transactions.map(normalizeTransaction),
  };
}

export async function getFinancialData(datasetId = DATASET_ID) {
  const params = new URLSearchParams({ datasetId });
  return normalizeFinancialData(await api(`/user-data?${params.toString()}`, {
    method: "GET",
  }));
}
