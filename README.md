# Guide

Before you start, you need to prepare your environment:

1. Clone repository

2. Fill in the variable in .env

| Variable Name       | Description                                                                                              |
|---------------------|----------------------------------------------------------------------------------------------------------|
| `SUBNET`            | The pool of addresses from which IPs will be assigned. The default mask is /24, so no need to specify it. |
| `forwardSubnets`    | Internal subnet for clients and the pool of addresses issued by Kubernetes. Multiple subnets can be separated by commas. |
| `ADMIN_PASSWORD`    | The password for the admin user.                                                                         |
| `ADMIN_IP`          | The IP address of the admin.                                                                             |
| `KEYCLOAK_URL`      | The URL for the Keycloak server.                                                                         |
| `KEYCLOAK_REALM`    | The realm for Keycloak authentication.                                                                   |
| `KEYCLOAK_CLIENT_ID`| The client ID for Keycloak authentication.                                                               |


3. Run docker compose amg check logs if all is OK
```docker-compose up -d --build```

4. Generate openvpn certificate
```docker exec -it vpnServer cat /etc/openvpn/client.ovpn | tee -a client.ovpn```
