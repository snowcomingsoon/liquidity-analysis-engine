# Candles squid: processor and GraphQL API from one image (the command picks).
FROM node:22-alpine AS build
WORKDIR /squid
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY tsconfig.json schema.graphql ./
COPY src ./src
RUN npx tsc && npm prune --omit=dev

FROM node:22-alpine
WORKDIR /squid
ENV NODE_ENV=production
COPY --from=build /squid/node_modules ./node_modules
COPY --from=build /squid/lib ./lib
COPY package.json schema.graphql ./
COPY db ./db
# Processor by default; the API service runs `npx squid-graphql-server`.
CMD ["sh", "-c", "npx squid-typeorm-migration apply && node lib/main.js"]
