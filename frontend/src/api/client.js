const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8080";

async function apiRequest(path, options = {}) {
  let response;
  try {
    const isFormData = options.body instanceof FormData;
    response = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers: { ...(!isFormData ? { "Content-Type": "application/json" } : {}), ...(options.headers || {}) },
    });
  } catch {
    throw new Error("백엔드 서버에 연결할 수 없습니다. MySQL과 Spring Boot 실행 상태를 확인해 주세요.");
  }
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.message || "요청을 처리하지 못했습니다.");
  return body;
}

export { apiRequest };
