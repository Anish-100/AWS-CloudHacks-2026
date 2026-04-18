import { api } from "./client";

export async function requestUpload(file) {
  return api("/upload", {
    method: "POST",
    body: JSON.stringify({
      fileName: file.name,
      contentType: file.type || "text/csv",
    }),
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

export async function getUploadStatus(batchId) {
  return api(`/status/${batchId}`);
}
