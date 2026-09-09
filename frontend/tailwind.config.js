/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        navy: {
          900: '#040810',
          800: '#070d1a',
          700: '#0a1222',
          600: '#0d1a2e',
          500: '#122040',
        },
        ice: {
          50: '#f0f8ff',
          100: '#dbeeff',
          200: '#b8deff',
          300: '#82c4ff',
          400: '#40a5f5',
          500: '#1a8adc',
          600: '#1070c0',
        },
        danger: '#ff4444',
        warning: '#ffaa00',
        safe: '#00e676',
        cyan: '#00e5ff',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      backdropBlur: {
        xs: '2px',
      },
    },
  },
  plugins: [],
};
