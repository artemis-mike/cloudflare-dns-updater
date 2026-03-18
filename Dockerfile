FROM python:3.14-alpine

RUN ["mkdir", "/cloudflare-updater"]
WORKDIR /cloudflare-updater
COPY ./source .
RUN ["python3", "-m", "pip", "install", "-r", "requirements.txt"]

ENTRYPOINT ["./entrypoint.sh"]