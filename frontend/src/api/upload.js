import { api } from "./client";

export async function requestUpload(file) {
  const params = new URLSearchParams({
    fileName: file.name,
    contentType: file.type || "text/csv",
  });

  return api(`/upload?${params.toString()}`, {
    method: "GET",
  });
}

export async function uploadToS3(uploadUrl, file) {
  const response = await fetch(uploadUrl, {
    method: "PUT",
    headers: {
      "Content-Type": file.type || "text/csv",
    },
    body: file,
  });

  if (!response.ok) {
    throw new Error("S3 upload failed");
  }
}

export async function uploadFinancialData(file) {
  return api("/upload-data", {
    method: "POST",
    headers: {
      "Content-Type": file.type || "text/csv",
    },
    body: file,
  });
}

export async function getUserData() {
  return api("/user-data", {
    method: "GET",
  });
}

export async function getUploadStatus(batchId) {
  return api(`/status/${batchId}`);
}
