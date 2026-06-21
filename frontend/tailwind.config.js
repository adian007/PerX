/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ['class'],
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        background: '#F4F1EA',
        foreground: '#1A1A1A',
        card: '#FAF9F5',
        accent: '#8B4513',
        muted: 'rgba(26, 26, 26, 0.55)',
        border: 'rgba(26, 26, 26, 0.12)',
        ink: '#1A1A1A',
        cream: '#F4F1EA',
        paper: '#FAF9F5',
        sienna: '#8B4513',
      },
      fontFamily: {
        display: ['"Cormorant Garamond"', 'Georgia', 'serif'],
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'monospace'],
      },
      borderRadius: {
        lg: '0',
        md: '0',
        sm: '0',
      },
      boxShadow: {
        none: 'none',
      },
    },
  },
  plugins: [],
}
