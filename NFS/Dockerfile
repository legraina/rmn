FROM ubuntu

RUN apt update && apt -y upgrade && apt install -y systemctl nfs-server

EXPOSE 2049

COPY docker-entrypoint.sh /usr/local/bin

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
