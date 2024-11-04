FROM python:3.9-slim

# Set working direction and install dependency packages
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy service packages
COPY service/ ./service/
# Create theia user and switch to user
RUN useradd --uid 1000 theia && chown -R theia /app
USER theia
# Open port and run service
EXPOSE 8080
CMD ["gunicorn", "--bind=0.0.0.0:8080", "--log-level=info", "service:app"]