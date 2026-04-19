const API_BASE_URL =
  import.meta.env.VITE_API_URL || import.meta.env.VITE_API_BASE_URL || "";

export function hasApiBaseUrl() {
  return Boolean(API_BASE_URL);
}

export async function api(path, options = {}) {
  if (!API_BASE_URL) {
    throw new Error("Missing VITE_API_URL");
  }

  const headers = {
    ...(options.headers || {}),
  };

  if (options.body && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers,
    ...options,
  });

  if (response.status === 204) {
    return null;
  }

  const payload = await response.json().catch(() => null);

  if (!response.ok) {
    const message = payload?.detail || payload?.message || `API error ${response.status}`;
    throw new Error(message);
  }

  return payload;
}
