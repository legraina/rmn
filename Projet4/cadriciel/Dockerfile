#stage 1
FROM node:16.13.0 as node
WORKDIR /app

COPY *.json .
RUN npm install

COPY . .
RUN npm run prod

#stage 2
FROM nginx:alpine
COPY --from=node /app/dist/cadriciel /usr/share/nginx/html
