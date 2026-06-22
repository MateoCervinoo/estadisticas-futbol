FROM node:20-slim

WORKDIR /app

# Copiamos el package.json que creamos
COPY package.json ./

# Si tenés un package-lock.json lo copia, si no, lo ignora y no rompe el build
COPY package-lock.json* ./

# Instalamos las dependencias. Si no hay lockfile, usa npm install automáticamente
RUN npm install

# Copiamos el resto del código del frontend
COPY . .

EXPOSE 3000

CMD ["npm", "run", "dev"]