import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./features/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        valmet: {
          green: "#2E7D32",
          darkgreen: "#1B5E20",
          lightgreen: "#E8F5E9",
          accent: "#4CAF50",
        },
        abb: {
          red: "#D60000",
          darkred: "#A30000",
          lightred: "#FF4D4D",
          slate: "#0F172A",
          darkgray: "#1E293B",
          midgray: "#334155",
          lightgray: "#F1F5F9",
          cardbg: "#FFFFFF",
          border: "#E2E8F0"
        }
      },
      fontFamily: {
        mono: ["JetBrains Mono", "Courier New", "monospace"],
      }
    },
  },
  plugins: [],
};
export default config;
