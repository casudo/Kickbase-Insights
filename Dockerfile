FROM ubuntu 

### Set working directory and copy files
RUN mkdir /code
WORKDIR /code
ADD . /code/

### Make script executable
RUN chmod 770 /code/main.py

### Install dependencies
RUN apt update && apt upgrade -y
RUN apt install tree nano python3 pip nodejs npm -y
RUN pip install -r requirements.txt

### Set entrypoint
### https://stackoverflow.com/a/29745541
ENTRYPOINT ["python3", "-u", "/code/entrypoint.py"]