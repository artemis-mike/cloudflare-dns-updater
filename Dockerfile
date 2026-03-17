FROM python:3.13-alpine

RUN ["mkdir", "/cloudflare-updater"]
RUN ["python3", "-m", "pip", "install", "requests", "chardet"]
WORKDIR /cloudflare-updater
COPY ./source .

ENTRYPOINT ["./entrypoint.sh"]