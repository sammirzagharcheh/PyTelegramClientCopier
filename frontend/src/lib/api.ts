import axios from 'axios';

const API_BASE = '/api';

export const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  if (config.data instanceof FormData) {
    if (config.headers) {
      delete config.headers['Content-Type'];
    }
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      const refresh = localStorage.getItem('refresh_token');
      if (refresh) {
        try {
          const { data } = await axios.post(`${API_BASE}/auth/refresh`, {
            refresh_token: refresh,
          });
          localStorage.setItem('access_token', data.access_token);
          originalRequest.headers.Authorization = `Bearer ${data.access_token}`;
          return api(originalRequest);
        } catch {
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          window.location.href = '/login';
        }
      } else {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

export type User = {
  id: number;
  email: string;
  name: string | null;
  role: string;
  status: string;
  timezone?: string | null;
};

// Transforms
export type TransformRuleType = 'text' | 'regex' | 'emoji' | 'media' | 'template';

export type Transform = {
  id: number;
  mapping_id: number;
  rule_type: TransformRuleType;
  find_text: string | null;
  replace_text: string | null;
  regex_pattern: string | null;
  regex_flags: string | null;
  replacement_media_asset_id: number | null;
  apply_to_media_types: string | null;
  enabled: boolean;
  priority: number;
  created_at: string | null;
};

export type TransformCreate = {
  rule_type: TransformRuleType;
  find_text?: string | null;
  replace_text?: string | null;
  regex_pattern?: string | null;
  regex_flags?: string | null;
  replacement_media_asset_id?: number | null;
  apply_to_media_types?: string | null;
  enabled?: boolean;
  priority?: number;
};

export type TransformUpdate = Partial<Omit<TransformCreate, 'rule_type'>> & { rule_type?: TransformRuleType };

// Media assets
export type MediaAsset = {
  id: number;
  user_id: number;
  name: string;
  file_path: string;
  media_kind: string;
  mime_type: string | null;
  size_bytes: number;
  created_at: string;
};
