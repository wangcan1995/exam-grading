# 前端构建 + Nginx 部署
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json ./
RUN npm install --registry=https://registry.npmmirror.com
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
# SPA 路由回退 + API 反代到后端
RUN printf 'server {\n\
  listen 80;\n\
  location / { root /usr/share/nginx/html; try_files $uri $uri/ /index.html; }\n\
  location /api/ { proxy_pass http://backend:8000; }\n\
}' > /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
