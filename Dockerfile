FROM python:3.10-bullseye

COPY requirements.txt /tmp/pip-tmp/
RUN pip3 --disable-pip-version-check --no-cache-dir install -r /tmp/pip-tmp/requirements.txt \
    && rm -rf /tmp/pip-tmp

WORKDIR /home
COPY . .

EXPOSE 8501

ENTRYPOINT [ "streamlit", "run", "/home/app.py", "--server.enableCORS", "false", "--server.enableXsrfProtection", "false" ]
