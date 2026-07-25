export const appConfig = {
  name: "CrimeLens AI",
  apiBaseUrl: process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1",
  features: {
    ai: process.env.NEXT_PUBLIC_AI_ENABLED === "true",
    ml: process.env.NEXT_PUBLIC_ML_ENABLED === "true",
    network: process.env.NEXT_PUBLIC_NETWORK_ENABLED === "true",
  },
} as const;
