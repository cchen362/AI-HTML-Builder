const STATUS_MESSAGES: Record<number, string> = {
  400: 'The request was invalid. Please check your input.',
  401: 'Your session has expired. Please log in again.',
  403: "You don't have permission to do that.",
  404: "This resource wasn't found. It may have been deleted.",
  413: 'File too large.',
  429: 'Too many requests. Please wait a moment and try again.',
  500: 'Something went wrong on the server. Try again in a moment.',
  502: 'Server is temporarily unavailable. Try again shortly.',
  503: 'Server is temporarily unavailable. Try again shortly.',
};

export function humanizeError(error: unknown): string {
  if (error instanceof TypeError && error.message.includes('fetch')) {
    return 'Server connection lost. Check your network and try again.';
  }
  if (error instanceof Error) {
    const match = error.message.match(/^(\d{3})\s/);
    if (match) {
      const code = parseInt(match[1], 10);
      return STATUS_MESSAGES[code] || `Server error (${code}). Please try again.`;
    }
    return error.message;
  }
  return 'An unexpected error occurred. Please try again.';
}
