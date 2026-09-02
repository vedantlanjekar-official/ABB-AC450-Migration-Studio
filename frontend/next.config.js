/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Keep development and production artifacts separate so a production build
  // cannot invalidate a running local development server.
  distDir: process.env.NODE_ENV === 'development' ? '.next-dev' : '.next',
  async rewrites() {
    // Production browser calls same-origin `/api/*`; Vercel proxies to Render.
    // Set BACKEND_URL on Vercel to: https://<render-service>.onrender.com/api/:path*
    const backend =
      process.env.BACKEND_URL ||
      (process.env.NODE_ENV === 'development'
        ? 'http://127.0.0.1:8002/api/:path*'
        : 'https://valmet-abb-ac450-api.onrender.com/api/:path*');

    return [
      {
        source: '/api/:path*',
        destination: backend,
      },
    ];
  },
};

module.exports = nextConfig;
