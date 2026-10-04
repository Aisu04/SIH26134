/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      boxShadow: {
        glow: '0 0 0 1px rgba(251, 191, 36, 0.24), 0 20px 45px rgba(15, 23, 42, 0.5)',
      },
    },
  },
  plugins: [],
}

