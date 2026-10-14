/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        bangla: ["'Hind Siliguri'", "system-ui", "sans-serif"],
      },
      colors: {
        // Bangladesh flag colors (official hex values).
        "bd-green": "#006A4E",
        "bd-red": "#F42A41",
      },
    },
  },
  plugins: [],
};
