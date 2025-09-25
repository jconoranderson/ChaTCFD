/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{js,jsx,ts,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        tcfd: {
          orange: '#F48120',
          navy: '#1E293B',
          sky: '#38BDF8',
          cream: '#FFF7ED',
        },
      },
      boxShadow: {
        card: '0 10px 30px rgba(30,41,59,0.12)',
      },
    },
  },
  plugins: [],
};
