FROM node:24-alpine AS build
WORKDIR /app
COPY package*.json .npmrc ./
RUN npm ci --ignore-scripts --no-audit --no-fund
COPY . ./
RUN npm run build

FROM alpine:3.23
COPY --from=build /app/build /build
CMD ["sh", "-c", "cp -a /build/. /frontend/"]
