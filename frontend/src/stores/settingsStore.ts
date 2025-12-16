import { create } from 'zustand';
import { persist } from 'zustand/middleware';

type Theme = 'light' | 'dark' | 'system';

interface SettingsState {
  theme: Theme;
  voiceMode: 'push_to_talk' | 'vad';
  
  setTheme: (theme: Theme) => void;
  setVoiceMode: (mode: 'push_to_talk' | 'vad') => void;
  getEffectiveTheme: () => 'light' | 'dark';
}

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set, get) => ({
      theme: 'system',
      voiceMode: 'push_to_talk',

      setTheme: (theme: Theme) => {
        set({ theme });
        applyTheme(theme);
      },

      setVoiceMode: (mode) => set({ voiceMode: mode }),

      getEffectiveTheme: () => {
        const { theme } = get();
        if (theme === 'system') {
          return window.matchMedia('(prefers-color-scheme: dark)').matches
            ? 'dark'
            : 'light';
        }
        return theme;
      },
    }),
    {
      name: 'livetalk-settings',
    }
  )
);

function applyTheme(theme: Theme) {
  const root = document.documentElement;
  const effectiveTheme =
    theme === 'system'
      ? window.matchMedia('(prefers-color-scheme: dark)').matches
        ? 'dark'
        : 'light'
      : theme;

  root.classList.remove('light', 'dark');
  root.classList.add(effectiveTheme);
}

// Initialize theme on load
if (typeof window !== 'undefined') {
  const stored = localStorage.getItem('livetalk-settings');
  if (stored) {
    try {
      const settings = JSON.parse(stored);
      applyTheme(settings.state?.theme || 'system');
    } catch {
      applyTheme('system');
    }
  } else {
    applyTheme('system');
  }

  // Listen for system theme changes
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
    const theme = useSettingsStore.getState().theme;
    if (theme === 'system') {
      applyTheme('system');
    }
  });
}
