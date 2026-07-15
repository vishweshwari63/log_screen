/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      borderRadius: {
        '2xl': '16px',
        'xl': '12px',
      },
      boxShadow: {
        'soft': '0 8px 30px rgba(0, 0, 0, 0.08)',
        'soft-dark': '0 8px 30px rgba(0, 0, 0, 0.35)',
      },
      colors: {
        themeLight: {
          bg: '#F8FAFC',
          card: '#FFFFFF',
          border: '#E2E8F0',
          primary: '#2563EB',
          accent: '#0EA5E9',
          text: '#0F172A',
          secText: '#64748B',
          success: '#16A34A',
          warning: '#F59E0B',
          danger: '#DC2626'
        },
        themeDark: {
          bg: '#0B1220',
          card: '#111827',
          secCard: '#1F2937',
          border: '#2D3748',
          primary: '#3B82F6',
          accent: '#14B8A6',
          text: '#F8FAFC',
          secText: '#94A3B8',
          hover: '#1E293B',
          success: '#22C55E',
          warning: '#FBBF24',
          danger: '#EF4444'
        }
      }
    },
  },
  plugins: [],
}
