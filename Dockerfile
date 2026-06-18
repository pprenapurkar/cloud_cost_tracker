FROM python:3.11-slim

WORKDIR /app

# Install deps first so this layer caches when only code changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the project.
COPY . .

# Generate sample data, then run the pipeline once and exit.
CMD ["sh", "-c", "python generate_sample_data.py && python -m src.costint.pipeline"]
