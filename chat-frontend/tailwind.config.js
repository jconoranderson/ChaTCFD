/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,jsx}",
  ],
  theme: {
    extend: {
      colors: {
        tcfdorange: "#F7931E", // Custom TCFD orange
      },
    },
  },
  plugins: [],
}
