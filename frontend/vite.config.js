import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// ✅ Adjust this only if you want to test locally without CORS.
// Leave it commented out if you’ll deploy to Vercel and call Lambda directly.
const LOCAL_LAMBDA_URL = "https://YOUR-LAMBDA-FUNCTION-URL.lambda-url.us-east-1.on.aws";

export default defineConfig({
  plugins: [react()],

  // Optional: lets you run `npm run dev` and call your Lambda without CORS
  server: {
    proxy: {
      // Uncomment if needed:
      // "/api": {
      //   target: LOCAL_LAMBDA_URL,
      //   changeOrigin: true,
      //   rewrite: (path) => path.replace(/^\/api/, ""),
      // },
    },
  },

  // Optional for Vercel or static hosting
  build: {
    outDir: "dist",
  },
});
