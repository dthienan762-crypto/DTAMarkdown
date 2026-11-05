import React from 'react';
import { Sun, Moon, Laptop } from 'lucide-react';
import { useTheme, Theme } from '../context/ThemeContext';
import { Locale } from '../lib/i18n';

interface ThemeToggleProps {
  locale?: Locale;
}

export const ThemeToggle: React.FC<ThemeToggleProps> = ({ locale = 'vi' }) => {
  const { theme, setTheme } = useTheme();

  const options: Array<{ value: Theme; labelVi: string; labelEn: string; icon: React.ReactNode }> = [
    {
      value: 'light',
      labelVi: 'Sáng',
      labelEn: 'Light',
      icon: <Sun className="w-3.5 h-3.5" />,
    },
    {
      value: 'dark',
      labelVi: 'Tối',
      labelEn: 'Dark',
      icon: <Moon className="w-3.5 h-3.5" />,
    },
    {
      value: 'system',
      labelVi: 'Hệ thống',
      labelEn: 'System',
      icon: <Laptop className="w-3.5 h-3.5" />,
    },
  ];

  return (
    <div className="flex items-center bg-slate-100 dark:bg-slate-950/80 p-0.5 rounded-lg border border-slate-200 dark:border-slate-800 text-xs select-none">
      {options.map((opt) => {
        const isActive = theme === opt.value;
        const label = locale === 'vi' ? opt.labelVi : opt.labelEn;

        return (
          <button
            key={opt.value}
            type="button"
            onClick={() => setTheme(opt.value)}
            className={`flex items-center gap-1 px-2 py-1 rounded-md transition-all ${
              isActive
                ? 'bg-indigo-600 text-white font-medium shadow-sm'
                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200'
            }`}
            title={`Giao diện: ${label}`}
          >
            {opt.icon}
            <span className="hidden xl:inline">{label}</span>
          </button>
        );
      })}
    </div>
  );
};

export default ThemeToggle;

