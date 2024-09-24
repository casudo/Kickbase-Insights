FROM ubuntu 

### Set working directory and copy files
WORKDIR /code
COPY . /code/

### Make script executable
RUN chmod 770 /code/main.py

### Install dependencies
RUN apt update && apt upgrade -y \
    && apt install -y python3 python3-pip curl tree nano

### Installs Node.js and npm directly
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs

### Update pip and install dependencies
RUN pip install --upgrade pip && pip install --upgrade -r requirements.txt

### Set environment variables / build arguments
### Will later be read from frontend
### Can be set with "docker build . -t ghcr.io/casudo/kickbase-insights:<version> --build-arg REACT_APP_VERSION=<version>"
ARG REACT_APP_VERSION 
ENV REACT_APP_VERSION=$REACT_APP_VERSION

### Set entrypoint
### https://stackoverflow.com/a/29745541
ENTRYPOINT ["python3", "-u", "/code/entrypoint.py"]