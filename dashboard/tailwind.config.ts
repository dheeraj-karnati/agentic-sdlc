import type { Config } from "tailwindcss";
import tailwindAnimate from "tailwindcss-animate";

const config: Config = {
  darkMode: ["class"],
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        /* ── D8X brand (marketing + dashboard) ── */
        d8x: {
          navy: "#1B4F72",
          "navy-deep": "#0F2D40",
          "navy-light": "#234E6F",
          gold: "#F5C518",
          "gold-light": "#F7D34E",
          blue: "#2E86C1",
          "blue-light": "#5DADE2",
          slate: "#1A1A2E",
          "slate-light": "#242442",
          /* Dashboard-specific */
          background: "#0D1117",
          surface: "#161B22",
          "surface-hover": "#1C2128",
          border: "#30363D",
          "border-hover": "#484F58",
          success: "#27AE60",
          warning: "#F39C12",
          danger: "#E74C3C",
          "text-primary": "#E6EDF3",
          "text-secondary": "#8B949E",
          "text-tertiary": "#484F58",
        },
        /* ── shadcn CSS variable colors ── */
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: { DEFAULT: "hsl(var(--primary))", foreground: "hsl(var(--primary-foreground))" },
        secondary: { DEFAULT: "hsl(var(--secondary))", foreground: "hsl(var(--secondary-foreground))" },
        destructive: { DEFAULT: "hsl(var(--destructive))", foreground: "hsl(var(--destructive-foreground))" },
        muted: { DEFAULT: "hsl(var(--muted))", foreground: "hsl(var(--muted-foreground))" },
        accent: { DEFAULT: "hsl(var(--accent))", foreground: "hsl(var(--accent-foreground))" },
        popover: { DEFAULT: "hsl(var(--popover))", foreground: "hsl(var(--popover-foreground))" },
        card: { DEFAULT: "hsl(var(--card))", foreground: "hsl(var(--card-foreground))" },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "Fira Code", "monospace"],
      },
      animation: {
        "flow-pulse": "flow-pulse 3s ease-in-out infinite",
        "fade-in": "fade-in 0.6s ease-out forwards",
        "slide-up": "slide-up 0.6s ease-out forwards",
        "terminal-blink": "terminal-blink 1s step-end infinite",
        "stage-pulse": "stage-pulse 2s ease-in-out infinite",
        "dot-flow": "dot-flow 1.5s linear infinite",
        "fade-up": "fade-up 0.4s ease-out forwards",
      },
      keyframes: {
        "flow-pulse": {
          "0%, 100%": { opacity: "0.4" },
          "50%": { opacity: "1" },
        },
        "fade-in": {
          from: { opacity: "0" },
          to: { opacity: "1" },
        },
        "slide-up": {
          from: { opacity: "0", transform: "translateY(20px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        "terminal-blink": {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0" },
        },
        "stage-pulse": {
          "0%, 100%": { boxShadow: "0 0 0 0 rgba(245, 197, 24, 0.4)" },
          "50%": { boxShadow: "0 0 0 8px rgba(245, 197, 24, 0)" },
        },
        "dot-flow": {
          "0%": { transform: "translateX(-8px)", opacity: "0" },
          "20%": { opacity: "1" },
          "80%": { opacity: "1" },
          "100%": { transform: "translateX(40px)", opacity: "0" },
        },
        "fade-up": {
          from: { opacity: "0", transform: "translateY(8px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
      },
    },
  },
  plugins: [tailwindAnimate],
};

export default config;
