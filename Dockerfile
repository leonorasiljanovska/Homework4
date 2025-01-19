
# Step 1: Use Miniconda as the base image
FROM continuumio/miniconda3:latest

# Step 2: Set the working directory in the container
WORKDIR /app

# Step 3: Copy the Conda environment file to the container
COPY environment.yml .

# Step 4: Create the Conda environment
RUN conda env create -f environment.yml

# Step 5: Activate the environment by default
# (Conda environments need to be activated explicitly in Docker)
RUN echo "conda activate tensorflow_env" >> ~/.bashrc
ENV PATH /opt/conda/envs/tensorflow_env/bin:$PATH

# Step 6: Copy the application code into the container
COPY . .

# Step 7: Expose the port (if necessary, e.g., for web apps)
EXPOSE 5000

# Step 8: Define the default command to run your app
CMD ["python", "company_controller.py"]



## Use the official Conda image as base
#FROM continuumio/miniconda3
#
## Set working directory
#WORKDIR /app
#
## Install system dependencies including PostgreSQL
#RUN apt-get update && apt-get install -y \
#    build-essential \
#    wget \
#    gcc \
#    g++ \
#    postgresql-server-dev-all \
#    libpq-dev \
#    && rm -rf /var/lib/apt/lists/*
#
## Install TA-Lib
#RUN wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz && \
#    tar -xvzf ta-lib-0.4.0-src.tar.gz && \
#    cd ta-lib/ && \
#    ./configure --prefix=/usr && \
#    make && \
#    make install && \
#    cd .. && \
#    rm -rf ta-lib-0.4.0-src.tar.gz ta-lib/
#
## Copy requirements.txt
#COPY requirements.txt .
#
## Create conda environment with the specific name
#RUN conda create -n tensorflow_env python=3.9
#
## Make RUN commands use the new environment
#SHELL ["conda", "run", "-n", "tensorflow_env", "/bin/bash", "-c"]
#
## Install major packages with conda first
#RUN conda install -y \
#    mkl \
#    mkl-service \
#    mkl_fft \
#    mkl_random \
#    numpy \
#    pandas \
#    scikit-learn \
#    scipy \
#    tensorflow \
#    keras \
#    h5py \
#    flask\
#    nltk\
#    && conda clean -afy
#
#RUN pip install flask flask-sqlalchemy flask-migrate psycopg2-binary
#
## Install pip packages with --ignore-installed to skip already installed packages
#RUN pip install --no-cache-dir --ignore-installed -r requirements.txt || true
#
## Copy your application code
#COPY . .
#
## Set the default command to activate conda environment and run your app
#CMD ["conda", "run", "-n", "tensorflow_env", "python", "company_controller.py"]
