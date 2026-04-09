FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

ARG APP_DIR
ARG INSTALL_METHOD=requirements
ARG INSTALL_TARGET=requirements.txt

WORKDIR /workspace
COPY ${APP_DIR} /workspace/${APP_DIR}
WORKDIR /workspace/${APP_DIR}

RUN python -m pip install --upgrade pip setuptools wheel \
    && if [ "$INSTALL_METHOD" = "requirements" ]; then pip install -r "$INSTALL_TARGET"; \
    elif [ "$INSTALL_METHOD" = "editable" ]; then pip install -e "$INSTALL_TARGET"; \
    else echo "Unsupported INSTALL_METHOD: $INSTALL_METHOD" >&2; exit 1; \
    fi
