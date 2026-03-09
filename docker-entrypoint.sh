#!/bin/sh
# Replace placeholders with environment variables
sed -i "s|__API_URL__|${API_URL:-http://localhost:3000}|g" /usr/share/nginx/html/index.html
sed -i "s|__API_KEY__|${API_KEY:-}|g" /usr/share/nginx/html/index.html
exec nginx -g 'daemon off;'
