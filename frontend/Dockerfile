# syntax=docker/dockerfile:1

# --- deps: install node_modules once, shared layer ------------------------
FROM node:24-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm install

# --- dev: live-reload dev server -------------------------------------------
# Source is bind-mounted by docker-compose for live reload; no COPY here.
FROM node:24-alpine AS dev
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY package.json package-lock.json ./
CMD ["npm", "run", "dev"]

# --- build: compiles the standalone production output ---------------------
FROM deps AS build
WORKDIR /app
COPY . .
RUN npm run build

# --- prod: minimal runtime image -------------------------------------------
FROM node:24-alpine AS prod
WORKDIR /app
ENV NODE_ENV=production
COPY --from=build /app/public ./public
COPY --from=build /app/.next/standalone ./
COPY --from=build /app/.next/static ./.next/static
CMD ["node", "server.js"]
