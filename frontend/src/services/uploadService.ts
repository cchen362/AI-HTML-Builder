export interface UploadResult {
  filename: string;
  file_type: string;
  content_type: 'text' | 'data';
  content: string;
  data_preview: string | null;
  row_count: number | null;
  columns: string[] | null;
}

export interface UploadResponse {
  success: boolean;
  data: UploadResult;
  suggested_prompt: string;
}

const ALLOWED_EXTENSIONS = ['.txt', '.md', '.docx', '.pdf', '.csv', '.xlsx'];
const MAX_SIZE_MB = 50;

/** Client-side file validation before upload. Returns error string or null. */
export function validateFileClient(file: File): string | null {
  const dotIdx = file.name.lastIndexOf('.');
  const ext = dotIdx >= 0 ? file.name.slice(dotIdx).toLowerCase() : '';
  if (!ALLOWED_EXTENSIONS.includes(ext)) {
    return `File type "${ext || '(none)'}" not allowed. Allowed: ${ALLOWED_EXTENSIONS.join(', ')}`;
  }
  if (file.size > MAX_SIZE_MB * 1024 * 1024) {
    return `File size exceeds ${MAX_SIZE_MB}MB limit`;
  }
  return null;
}

/** Upload a file to the backend and get extracted content + suggested prompt. */
export async function uploadFile(file: File): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch('/api/upload', {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Upload failed' }));
    throw new Error(error.detail || `Upload failed (${response.status})`);
  }

  return response.json();
}
