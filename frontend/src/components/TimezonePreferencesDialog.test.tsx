import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { TimezonePreferencesDialog } from './TimezonePreferencesDialog';

const mockRefreshUser = vi.fn();
vi.mock('../store/AuthContext', () => ({
  useAuth: () => ({ user: { timezone: null }, refreshUser: mockRefreshUser }),
}));

vi.mock('./Toast', () => ({
  useToast: () => ({ show: vi.fn() }),
}));

const mockPatch = vi.fn();
vi.mock('../lib/api', () => ({
  api: {
    patch: (...args: unknown[]) => mockPatch(...args),
  },
}));

describe('TimezonePreferencesDialog', () => {
  const onClose = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    mockPatch.mockResolvedValue({ data: { timezone: 'America/New_York' } });
  });

  it('renders dialog with searchable dropdown and Save button', () => {
    render(
      <QueryClientProvider client={new QueryClient()}>
        <TimezonePreferencesDialog onClose={onClose} />
      </QueryClientProvider>
    );
    expect(screen.getByRole('combobox', { name: /timezone/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Save' })).toBeInTheDocument();
  });

  it('calls PATCH /auth/me with timezone on Save', async () => {
    render(
      <QueryClientProvider client={new QueryClient()}>
        <TimezonePreferencesDialog onClose={onClose} />
      </QueryClientProvider>
    );
    fireEvent.focus(screen.getByRole('combobox', { name: /timezone/i }));
    fireEvent.click(screen.getByRole('option', { name: /America\/New_York/ }));
    fireEvent.click(screen.getByRole('button', { name: 'Save' }));
    await waitFor(() => {
      expect(mockPatch).toHaveBeenCalledWith('/auth/me', { timezone: 'America/New_York' });
    });
  });

  it('calls refreshUser after successful save', async () => {
    render(
      <QueryClientProvider client={new QueryClient()}>
        <TimezonePreferencesDialog onClose={onClose} />
      </QueryClientProvider>
    );
    fireEvent.click(screen.getByRole('button', { name: 'Save' }));
    await waitFor(() => {
      expect(mockRefreshUser).toHaveBeenCalled();
    });
  });

  it('sends null when Use my device timezone is selected', async () => {
    render(
      <QueryClientProvider client={new QueryClient()}>
        <TimezonePreferencesDialog onClose={onClose} />
      </QueryClientProvider>
    );
    fireEvent.focus(screen.getByRole('combobox', { name: /timezone/i }));
    fireEvent.click(screen.getByRole('option', { name: /Use my device timezone/i }));
    fireEvent.click(screen.getByRole('button', { name: 'Save' }));
    await waitFor(() => {
      expect(mockPatch).toHaveBeenCalledWith('/auth/me', { timezone: null });
    });
  });
});
