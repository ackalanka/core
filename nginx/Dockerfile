# ============================================
# CardioVoice - Nginx Dockerfile
# ============================================
# Configurable for dev or prod mode

FROM nginx:alpine

LABEL maintainer="CardioVoice Team"
LABEL description="CardioVoice Nginx Reverse Proxy"

# Remove default nginx config
RUN rm /etc/nginx/conf.d/default.conf

# Expose port
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost/health || exit 1

CMD ["nginx", "-g", "daemon off;"]
