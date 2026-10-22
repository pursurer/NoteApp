FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends iputils-ping \
    && rm -rf /var/lib/apt/lists/*
COPY web/requirements.txt /tmp/base-requirements.txt
COPY session03/requirements.txt /tmp/lab-requirements.txt
RUN pip install --no-cache-dir -r /tmp/base-requirements.txt -r /tmp/lab-requirements.txt
COPY web/ /app/
COPY session03/generate_key.py /app/
RUN printf 'import runpy\nrunpy.run_path("/app/test_comment_encryption.py", run_name="__main__")\n' > /app/test_homework.py
ENV NOTESAPP_LOG=/tmp/notesapp.log PYTHONDONTWRITEBYTECODE=1
EXPOSE 5000
ENTRYPOINT ["python", "runtime.py", "--migrate"]
CMD ["flask", "--app", "app", "run", "--host=0.0.0.0", "--port=5000", "--no-debugger", "--no-reload"]
