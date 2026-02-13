import { createContext, useCallback, useContext, useState } from 'react';

type ToastItem = { id: number; message: string };

const ToastContext = createContext<((message: string) => void) | null>(null);

export function useToast() {
  const show = useContext(ToastContext);
  if (!show) {
    return { show: () => {} };
  }
  return { show };
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const show = useCallback((message: string) => {
    const id = Date.now();
    setToasts((prev) => [...prev, { id, message }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 3500);
  }, []);

  return (
    <ToastContext.Provider value={show}>
      {children}
      <div
        className="fixed bottom-4 right-4 z-[100] flex flex-col gap-2 max-w-sm"
        aria-live="polite"
        aria-atomic="true"
      >
        {toasts.map((t) => (
          <div
            key={t.id}
            className="px-4 py-3 rounded-lg shadow-lg bg-emerald-600 text-white text-sm font-medium"
          >
            {t.message}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}
