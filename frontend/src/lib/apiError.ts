/** Pulls the FastAPI `detail` string out of an axios error when there is one. */
export function errorMessage(error: unknown, fallback = 'Please try again.'): string {
  if (
    error &&
    typeof error === 'object' &&
    'response' in error &&
    error.response &&
    typeof error.response === 'object' &&
    'data' in error.response &&
    error.response.data &&
    typeof error.response.data === 'object' &&
    'detail' in error.response.data
  ) {
    const detail = (error.response.data as { detail: unknown }).detail;
    if (typeof detail === 'string' && detail.trim()) return detail;
    if (detail && typeof detail === 'object' && 'message' in detail) {
      const message = (detail as { message: unknown }).message;
      if (typeof message === 'string' && message.trim()) return message;
    }
  }
  if (error instanceof Error && error.message) {
    // Axios's generic "Request failed with status code 500" is not useful to operators.
    if (!/^Request failed with status code \d+$/.test(error.message)) {
      return error.message;
    }
  }
  return fallback;
}
