FROM node:20-alpine AS build

WORKDIR /app

COPY frontend/package.json /app/package.json
COPY frontend/tsconfig.json /app/tsconfig.json
COPY frontend/tsconfig.app.json /app/tsconfig.app.json
COPY frontend/vite.config.ts /app/vite.config.ts
COPY frontend/index.html /app/index.html
COPY frontend/src /app/src

RUN npm install
RUN npm run build

FROM nginx:1.27-alpine

COPY infra/docker/frontend.nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

