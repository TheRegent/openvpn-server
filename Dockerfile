FROM alpine:3

RUN apk add --no-cache openvpn wget curl openssl iproute2 iptables net-tools bash python3 py3-urllib3 ipcalc jq && \
    cd /etc/src/ && \
    wget https://github.com/OpenVPN/easy-rsa/releases/download/v3.1.6/EasyRSA-3.1.6.tgz && \
    tar -xzf EasyRSA-3.1.6.tgz && \
    mv EasyRSA-3.1.6 easy-rsa 

COPY src/vars /etc/src/easy-rsa/vars

RUN python3 /exec.py

CMD ["python3", "exec.py"]
