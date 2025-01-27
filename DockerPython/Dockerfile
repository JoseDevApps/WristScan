# Use the official Ubuntu base image
FROM ubuntu:24.10

# Set environment variables
ENV CONDA_DIR=/opt/conda
ENV PATH=$CONDA_DIR/bin:$PATH

# Install dependencies
RUN apt-get update && apt-get install -y \
    wget \
    bzip2 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Download and install Anaconda
RUN wget https://repo.anaconda.com/archive/Anaconda3-2024.06-1-Linux-x86_64.sh -O ~/anaconda.sh && \
    bash ~/anaconda.sh -b -p $CONDA_DIR && \
    rm ~/anaconda.sh

# Create a new conda environment with Python 3.10
RUN conda create -n myenv python=3.10 -y

# Activate the conda environment and install pip (if necessary)
RUN conda init
RUN echo "conda activate myenv" >> ~/.bashrc && \
    /bin/bash -c "source ~/.bashrc && conda install pip -y"


# Generando un directorio de trabajo
RUN mkdir -p /codigo
WORKDIR /codigo
# Copiando la lista de requerimientos para django
COPY Requirements.txt .
COPY Requirements_pip.txt .

# Install Conda Requirements
# RUN conda install --file Requirements.txt
RUN /bin/bash -c "source activate myenv && conda install --file Requirements.txt && pip install -r Requirements_pip.txt"
# Set the default environment
CMD ["/bin/bash", "-c", "source activate myenv && exec bash"]