import { api } from "./client";

export async function getRecommendations() {
  return api("/recommendations");
}
