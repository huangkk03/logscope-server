#FROM python:3.11-slim
FROM harbor.server.finzech.com/public/python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# 先拷贝依赖清单，利用 Docker layer cache
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -U pip \
    && pip install --no-cache-dir -r /app/requirements.txt

# 再拷贝代码
COPY app /app/app

# 运行时会写入 /app/data 与 /app/logs（建议用 volume 挂载出来）
EXPOSE 8000

# 可用环境变量：
# - LOGSCOPE_AUTH_TOKEN: Bearer Token（默认 your-secret-admin-token，生产务必修改）
# - ES_HOSTS: ES hosts（逗号分隔），默认 http://localhost:9200
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

