FROM mcr.microsoft.com/vscode/devcontainers/python:3.10

# Instala Node.js (para React)
ARG NODE_VERSION=18
RUN curl -fsSL https://deb.nodesource.com/setup_${NODE_VERSION}.x | bash - \
    && apt-get install -y nodejs

# Opcional: instala utilitários extras
RUN apt-get update && apt-get install -y git