/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#ffffff',
          100: '#fafafa',
          200: '#f4f4f5',
          300: '#e4e4e7',
          400: '#d4d4d8',
          500: '#a1a1aa',
          600: '#71717a',
          700: '#3f3f46',
          800: '#27272a',
          900: '#18181b',
          950: '#09090b',
        },
        surface: {
          DEFAULT: 'var(--color-surface)',
          card: 'var(--color-surface-card)',
          border: 'var(--color-surface-border)',
          hover: 'var(--color-surface-hover)',
          muted: 'var(--color-surface-muted)',
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      animation: {
        'fade-in': 'fadeIn 0.3s ease-out',
        'slide-up': 'slideUp 0.4s ease-out',
        'pulse-slow': 'pulse 3s cubic-bezier(0.4,0,0.6,1) infinite',
        'shimmer': 'shimmer 2s linear infinite',
      },
      keyframes: {
        fadeIn: { from: { opacity: 0 }, to: { opacity: 1 } },
        slideUp: { from: { opacity: 0, transform: 'translateY(16px)' }, to: { opacity: 1, transform: 'translateY(0)' } },
        shimmer: { '0%': { backgroundPosition: '-200% 0' }, '100%': { backgroundPosition: '200% 0' } },
      },
    },
  },
  plugins: [],
}
