ARG BUILD_FROM
FROM ${BUILD_FROM}

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY server.py ./
COPY web /web

EXPOSE 80
CMD ["python3", "/app/server.py"]
