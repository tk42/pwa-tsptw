FROM python:3.10-bullseye

COPY requirements.txt /tmp/pip-tmp/
RUN pip3 --disable-pip-version-check --no-cache-dir install -r /tmp/pip-tmp/requirements.txt \
    && rm -rf /tmp/pip-tmp

WORKDIR /home
COPY . .

EXPOSE 8501

RUN find /usr/local/lib/python3.10/site-packages/streamlit -type f -iname "*.py" -print0 | xargs -0 sed -i 's/healthz/health-check/g'
RUN find /usr/local/lib/python3.10/site-packages/streamlit -type f -iname "*.js" -print0 | xargs -0 sed -i 's/healthz/health-check/g'

ENTRYPOINT [ "streamlit", "run", "main.py" ]
