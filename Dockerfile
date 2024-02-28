FROM python:alpine

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY migrations ./migrations
COPY scripts ./scripts
COPY static ./static
COPY templates ./templates
COPY *.py ./

EXPOSE 8000
CMD ["sh", "scripts/container_entrypoint.sh"]
