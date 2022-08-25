FROM jupyter/base-notebook:latest
USER jovyan
RUN conda install -y jupyter_contrib_nbextensions

USER root
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential \
    gfortran \
    file \
    wget \
    unzip \
    zlib1g-dev \
    bison \
    flex \
    libgmp-dev \
    libreadline-dev \
    libncurses5-dev \
    glpk-utils \
    libblas-dev \
    liblapack-dev \
    python3-dev \
    python3-pip && \
    rm -rf /var/lib/apt/lists/*

RUN pip install pyomo
