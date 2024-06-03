import os
import subprocess
import shutil
import re
import requests

def run_command(command, shell=False):
    process = subprocess.Popen(command, shell=shell, executable='/bin/bash', stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    if process.returncode != 0:
        raise subprocess.CalledProcessError(process.returncode, command, output=stdout, stderr=stderr)
    return stdout, stderr

def convert_mask(subnets):
    if subnets:
        subnets_list = subnets.split(',')
        for subnet in subnets_list:
            result = subprocess.run(['ipcalc', '-nm', subnet], capture_output=True, text=True)
            matches = re.findall(r'NETWORK=(\S+)|NETMASK=(\S+)', result.stdout)
            network, netmask = matches[0][0], matches[1][1]
            print(f'push "route {network} {netmask}"')

def setup_easyrsa():
    # Change directory to /etc/src/easy-rsa
    os.chdir('/etc/src/easy-rsa')

    # Initialize PKI
    run_command(['./easyrsa', 'init-pki'])

    # Build CA with no password
    run_command(['./easyrsa', '--batch', '--req-cn=cn_MqZtFvwq35w1vtVX', 'build-ca', 'nopass'])

    # Generate request for openvpn-server
    run_command('yes yes | ./easyrsa gen-req openvpn-server nopass', shell=True)

    # Sign the request
    run_command('yes yes | ./easyrsa sign-req server openvpn-server', shell=True)

    # Generate DH parameters
    run_command(['./easyrsa', 'gen-dh'])

    # Generate ta.key
    run_command(['openvpn', '--genkey', 'secret', 'ta.key'])

    # Create necessary directories
    os.makedirs('/etc/src/client', exist_ok=True)
    os.makedirs('/etc/src/server', exist_ok=True)
    os.makedirs('/etc/src/tmp', exist_ok=True)

    # Copy the necessary files
    shutil.copy('pki/ca.crt', '/etc/src/server/')
    shutil.copy('pki/issued/openvpn-server.crt', '/etc/src/server/')
    shutil.copy('pki/private/openvpn-server.key', '/etc/src/server/')
    shutil.copy('pki/ca.crt', '/etc/src/client/')
    shutil.copy('pki/dh.pem', '/etc/src/server/')
    shutil.copy('ta.key', '/etc/src/server/')

    # Change ownership of /etc/openvpn
    run_command(['chown', 'nobody:nobody', '-R', '/etc/openvpn'])

def main():
    setup_easyrsa()

    # Copy files
    shutil.copytree('/etc/openvpn-bootstrap/', '/etc/src/', dirs_exist_ok=True)

    # Modify server.conf and client.ovpn with subnet and server_ip
    subnet = os.getenv('SUBNET')
    server_ip = requests.get('http://ifconfig.me').text.strip()

    with open('/etc/src/server.conf', 'r') as file:
        server_conf = file.read()
    server_conf = server_conf.replace('<subnet>', subnet).replace('<server_ip>', server_ip)
    with open('/etc/src/server.conf', 'w') as file:
        file.write(server_conf)

    with open('/etc/src/client.ovpn', 'r') as file:
        client_conf = file.read()
    client_conf = client_conf.replace('<server_ip>', server_ip)
    with open('/etc/src/client.ovpn', 'w') as file:
        file.write(client_conf)

    forward_subnets = os.getenv('forwardSubnets')
    if forward_subnets:
        convert_mask(forward_subnets)
        with open('/etc/src/server.conf', 'a') as file:
            file.write(f'\npush "route {forward_subnets}"')

    # Append CA certificate to client.ovpn
    with open('/etc/src/client.ovpn', 'a') as file:
        file.write('<ca>\n')
        with open('/etc/src/server/ca.crt', 'r') as ca_file:
            file.write(ca_file.read())
        file.write('</ca>\n')

    # Substitute other variables
    replacements = {
        '<ADMIN_PASSWORD>': os.getenv('ADMIN_PASSWORD'),
        '<ADMIN_IPs>': os.getenv('ADMIN_IPs'),
        '<KEYCLOAK_URL>': os.getenv('KEYCLOAK_URL'),
        '<KEYCLOAK_REALM>': os.getenv('KEYCLOAK_REALM'),
        '<KEYCLOAK_CLIENT_ID>': os.getenv('KEYCLOAK_CLIENT_ID'),
    }

    with open('/etc/src/server.conf', 'r') as file:
        server_conf = file.read()
    for key, value in replacements.items():
        server_conf = server_conf.replace(key, value)
    with open('/etc/src/server.conf', 'w') as file:
        file.write(server_conf)

    # Print the server.conf for verification
    print(server_conf)

    # Enable IP forwarding
    run_command(['sysctl', '-w', 'net.ipv4.ip_forward=1'])

    # Set up iptables rules
    run_command(['iptables', '-P', 'FORWARD', 'DROP'])
    run_command(['iptables', '-A', 'FORWARD', '-d', f'{subnet}/24,{forward_subnets}', '-j', 'ACCEPT'])
    run_command(['iptables', '-A', 'FORWARD', '-m', 'state', '--state', 'RELATED,ESTABLISHED', '-j', 'ACCEPT'])
    run_command(['iptables', '-t', 'nat', '-A', 'POSTROUTING', '-j', 'MASQUERADE'])

    # Create /dev/net/tun if it doesn't exist
    os.makedirs('/dev/net', exist_ok=True)
    try:
        os.mknod('/dev/net/tun', 0o600 | os.makedev(10, 200))
    except FileExistsError:
        pass
    os.chmod('/dev/net/tun', 0o600)

    # Start OpenVPN
    run_command(['openvpn', '--config', '/etc/src/server.conf'])

if __name__ == "__main__":
    main()

