import { api } from "./client";

export async function getQuickSightEmbedUrl() {
  return api("/quicksight/embed");
}
