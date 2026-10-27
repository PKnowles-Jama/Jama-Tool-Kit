ARG PYTHON_IMAGE
FROM ${PYTHON_IMAGE}
WORKDIR /app
COPY . /app
RUN python -m pip install --no-index --find-links=/app/wheelhouse -r requirements.txt
USER 10001:10001
EXPOSE 8090
CMD ["python", "viewer.py", "serve", "--config", "/run/config.json", "--host", "0.0.0.0"]
