/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',  // Enable dark mode with class
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}", // Path to files for Tailwind processing
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}
