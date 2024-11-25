FROM node
WORKDIR /app

COPY ../package.json ../package-lock.json ./
COPY ./Pet_Finder .

RUN npm install

EXPOSE 5000

CMD [ "sh", "-c", "node server.js" ]

# docker system prune -a
