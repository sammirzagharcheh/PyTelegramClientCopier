import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { MappingDetail } from './MappingDetail';

const mockApiGet = vi.fn();
const mockApiPost = vi.fn();
vi.mock('../../lib/api', () => ({
  api: {
    get: (...args: unknown[]) => mockApiGet(...args),
    put: vi.fn().mockResolvedValue({ data: {} }),
    delete: vi.fn().mockResolvedValue({ data: { status: 'ok' } }),
    post: (...args: unknown[]) => mockApiPost(...args),
    patch: vi.fn().mockResolvedValue({ data: {} }),
  },
}));

vi.mock('../../store/AuthContext', () => ({
  useAuth: () => ({ user: { id: 1, name: 'Test', email: 'test@test.com' } }),
}));

vi.mock('../../components/Toast', () => ({
  useToast: () => ({ show: vi.fn() }),
}));

describe('MappingDetail', () => {
  const defaultMapping = {
    id: 1,
    user_id: 1,
    source_chat_id: 10,
    dest_chat_id: 20,
    enabled: true,
    name: 'Test',
    source_chat_title: 'Source',
    dest_chat_title: 'Dest',
    telegram_account_id: null,
    created_at: '2020-01-01T00:00:00Z',
    send_delay_ms: 0,
    sync_edits: false,
    edit_strategy: 'replace_text',
    sync_deletes: false,
    copy_webhook_url: null,
    copy_webhook_secret: null,
  };

  beforeEach(() => {
    vi.clearAllMocks();
    mockApiPost.mockResolvedValue({
      data: {
        passes_filters: true,
        passes_schedule: true,
        transformed_text: 'preview-out',
      },
    });
    mockApiGet.mockImplementation(async (url: string) => {
      if (url === '/mappings/1') return { data: defaultMapping };
      if (url === '/mappings/1/filters') return { data: [] };
      if (url === '/mappings/1/transforms') return { data: [] };
      if (url.startsWith('/media-assets')) return { data: [] };
      if (url === '/mappings/1/schedule')
        return {
          data: {
            mon_start_utc: null,
            mon_end_utc: null,
            tue_start_utc: null,
            tue_end_utc: null,
            wed_start_utc: null,
            wed_end_utc: null,
            thu_start_utc: null,
            thu_end_utc: null,
            fri_start_utc: null,
            fri_end_utc: null,
            sat_start_utc: null,
            sat_end_utc: null,
            sun_start_utc: null,
            sun_end_utc: null,
          },
        };
      if (url === '/users/me/schedule') return { data: {} };
      throw new Error(`Unexpected API call: ${url}`);
    });
  });

  function renderDetail(path = '/mappings/1') {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    return render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={[path]}>
          <Routes>
            <Route path="/mappings/:id" element={<MappingDetail />} />
            <Route path="/admin/mappings/:id" element={<MappingDetail />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    );
  }

  it('renders Schedule section heading', async () => {
    renderDetail();
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Schedule' })).toBeInTheDocument();
    });
  });

  it('shows Default schedule when no custom schedule', async () => {
    renderDetail();
    await waitFor(() => {
      expect(screen.getByText('Default')).toBeInTheDocument();
    });
  });

  it('shows Configure global schedule link when user owns mapping', async () => {
    renderDetail();
    await waitFor(() => {
      expect(screen.getByRole('link', { name: 'Configure global schedule' })).toBeInTheDocument();
    });
  });

  it('shows Switch to custom button', async () => {
    renderDetail();
    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Switch to custom' })).toBeInTheDocument();
    });
  });

  it('shows custom schedule form when mapping has custom schedule', async () => {
    mockApiGet.mockImplementation(async (url: string) => {
      if (url === '/mappings/1') return { data: defaultMapping };
      if (url === '/mappings/1/filters') return { data: [] };
      if (url === '/mappings/1/transforms') return { data: [] };
      if (url.startsWith('/media-assets')) return { data: [] };
      if (url === '/mappings/1/schedule')
        return {
          data: {
            mon_start_utc: '09:00',
            mon_end_utc: '17:00',
            tue_start_utc: '09:00',
            tue_end_utc: '17:00',
            wed_start_utc: null,
            wed_end_utc: null,
            thu_start_utc: null,
            thu_end_utc: null,
            fri_start_utc: null,
            fri_end_utc: null,
            sat_start_utc: null,
            sat_end_utc: null,
            sun_start_utc: null,
            sun_end_utc: null,
          },
        };
      if (url === '/users/me/schedule') return { data: {} };
      throw new Error(`Unexpected API call: ${url}`);
    });
    renderDetail();
    await waitFor(() => {
      expect(screen.getByText('Custom schedule for this mapping')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Switch to default' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Save schedule' })).toBeInTheDocument();
    });
  });

  it('runs pipeline preview via POST /mappings/:id/preview', async () => {
    renderDetail();
    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Preview pipeline' })).toBeInTheDocument();
    });
    fireEvent.click(screen.getByRole('button', { name: 'Preview pipeline' }));
    fireEvent.click(screen.getByRole('button', { name: 'Run preview' }));
    await waitFor(() => {
      expect(mockApiPost).toHaveBeenCalledWith(
        '/mappings/1/preview',
        expect.objectContaining({
          sample_text: '',
          media_type: 'text',
        })
      );
      expect(screen.getByText('preview-out')).toBeInTheDocument();
    });
  });
});
