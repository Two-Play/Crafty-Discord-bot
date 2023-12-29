FROM ubuntu:latest
LABEL authors="philippe"

ENTRYPOINT ["top", "-b"]