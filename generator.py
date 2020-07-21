import argparse
import glob
import json
import os
import subprocess
import sys
from ipaddress import IPv4Network


def main():
    ###
    ### NEED TO EDIT VALUES BELOW TO MATCH YOUR NETWORK ###
    ###
	
    # lighthouse_url=["lighthouse1.com:4242", "lighthouse2.com:8080"]
    lighthouse_url = ["my_fist_lighthouse.com:4242"]
	
    # lighthouse_ip=["192.168.22.1", "192.168.22.2"]
    lighthouse_ip = ["192.168.22.1"]
	
    # Required: name of the certificate authority
    ca_name = "My super awesome Nebula CA"
	
    # The internal network for the nebula Mesh to use
    network = IPv4Network('192.168.22.0/24')
	
    # Reserved addresses for lighthouse and such that we don't use for nodes
    reserved_ips = {'192.168.22.1', '192.168.22.2', '192.168.22.3', '192.168.22.4', '192.168.22.5',
                    '192.168.22.6', '192.168.22.7', '192.168.22.8', '192.168.22.9', '192.168.22.10'}
	
    ###
    ### END OF NEED TO EDIT !!! ###
    ###

    # Figure out which version of Nebula we need to run!
    if "linux" in sys.platform:
        my_platform = "linux"
    elif "win32" in sys.platform:
        my_platform = "windows"
    print("Platform is: " + my_platform)

    # Parsing commandline arguments
    parser = argparse.ArgumentParser(description='Nebula config file generator')

    parser.add_argument("-name", type=str,
                        help="specify the name for the new node",
                        required=True,
                        # default="mate.nebula",
                        )
    parser.add_argument("-ip", type=str,
                        help="specify the IP for the new node",
                        default="",
                        # default="192.168.22.11/24",
                        )
    parser.add_argument("-subnets", type=str,
                        help="specify the subnets for the new node",
                        default="",
                        # default="0.0.0.0/0,192.168.254.0/24,192.168.255.0/24",
                        )
    parser.add_argument("-groups", type=str,
                        help="specify the groups for the new node",
                        default="",
                        # default="red, blue",
                        )
    parser.add_argument("-lighthouse", type=bool,
                        help="Set this to True if this node is a lighthouse.",
                        default=False,
                        )

    args = parser.parse_args()

    # grab all crt files and track which IPs are already in use
    cert_names = list()
    cert_ips = list()
    files = [f for f in glob.glob("*.crt")]
    for f in files:
        if not "ca.crt" in f:
            if my_platform == "windows":
                output = subprocess.check_output(["nebula-cert.exe", "print", "-json", "-path", f])
            if my_platform == "linux":
                output = subprocess.check_output(["./nebula-cert", "print", "-json", "-path", f])

            cert_json = json.loads(output)
            cert_ips.append(cert_json["details"]["ips"][0].split('/')[0])
            cert_names.append(cert_json["details"]["name"])

    # Check if IP provided is usable
    if len(args.ip) > 0:
        if not str(args.ip).split('/')[0] in cert_ips:
            client_ip = args.ip
        else:
            print("IP already in use")
            exit(1)
    else:
        # find the next available IP
        hosts_iterator = (host for host in network.hosts() if str(host) not in reserved_ips)
        client_ip = str(next(hosts_iterator)) + '/24'
    print('Client IP: ' + client_ip)

    # Check if provided name is unique
    print("Certificate names found in directory: " + str(cert_names))
    if not args.name in cert_names:
        client_name = str(args.name)
    else:
        print("Name already in use")
        exit(1)

    # check and add subnets
    if len(args.subnets) > 0:
        client_subnets = args.subnets.split(',')
    else:
        client_subnets = []
    if len(args.groups) > 0:
        client_groups = args.groups.split(',')
    else:
        client_groups = []

    # Download required files
    if my_platform == "windows" and not os.path.isfile('nebula-cert.exe'):
        print("Downloading Nebula for Windows")
        import requests, zipfile, io
        r = requests.get("https://github.com/slackhq/nebula/releases/download/v1.2.0/nebula-windows-amd64.zip")
        z = zipfile.ZipFile(io.BytesIO(r.content))
        z.extractall()
    if my_platform == "linux" and not os.path.isfile('nebula-cert'):
        print("Downloading Nebula for Linux")
        import requests, tarfile, io
        r = requests.get("https://github.com/slackhq/nebula/releases/download/v1.2.0/nebula-linux-amd64.tar.gz")
        tar = tarfile.open(fileobj=io.BytesIO(r.content))
        tar.extractall()

    if not os.path.isfile('config.yml'):
        print("Downloading config template")
        import requests
        r = requests.get("https://raw.githubusercontent.com/slackhq/nebula/master/examples/config.yml")
        with open('config.yml', 'wb') as f:
            f.write(r.content)

    # parse out the config template
    my_list = list(read_template('config.yml'))

    # check / make ca certificates
    make_ca_certs(my_platform, ca_name)

    # check / make node certificates
    make_certs(my_platform, client_name, client_ip, client_subnets, client_groups)

    with open('ca.crt', 'r') as myfile:
        ca_cert = myfile.read().split('\n')
    with open(client_name + '.crt', 'r') as myfile:
        client_cert = myfile.read().split('\n')
    with open(client_name + '.key', 'r') as myfile:
        client_key = myfile.read().split('\n')

    # Now let's create a list containing the new config file
    newfile = list()
    newfile.append('# Nebula configuration file for: ' + client_name)
    newfile.append('# Nebula IP: ' + client_ip)
    for x in range(0, len(my_list)):
        line = my_list[x]
        if "ca: /etc/nebula/ca.crt" in line:
            newfile.append("  ca: |")
            for line in ca_cert:
                if line.strip() != "":
                    newfile.append("    " + line.strip())
        elif 'cert: /etc/nebula/host.crt' in line:
            newfile.append("  cert: |")
            for line in client_cert:
                if line.strip() != "":
                    newfile.append("    " + line.strip())
        elif 'key: /etc/nebula/host.key' in line:
            newfile.append("  key: |")
            for line in client_key:
                if line.strip() != "":
                    newfile.append("    " + line.strip())
        elif 'static_host_map:' in line:
            newfile.append('static_host_map:')
            if not args.lighthouse:
                for i in range(0, len(lighthouse_url)):
                    newfile.append('  "' + lighthouse_ip[i] + '": ["' + lighthouse_url[i] + '"]')
        elif '"192.168.100.1": ["100.64.22.11:4242"]' in line:
            pass
        elif 'am_lighthouse:' in line:
            if args.lighthouse:
                newfile.append('  am_lighthouse: true')
                newfile.append('  serve_dns: true')
                newfile.append('  dns:')
                newfile.append('    host: ' + client_ip.split('/')[0])
                newfile.append('    port: 5353')
            else:
                newfile.append('  am_lighthouse: false')
        elif 'hosts:' in line:
            newfile.append('  hosts:')
            if not args.lighthouse:
                for i in range(0, len(lighthouse_url)):
                    newfile.append('    - "' + lighthouse_ip[i] + '"')
        elif '- "192.168.100.1"' in line:
            pass
        elif 'unsafe_routes:' in line:
            newfile.append('  unsafe_routes:')
            newfile.append('    #- route: 0.0.0.0/0')
            newfile.append('    #  via: ' + lighthouse_ip[0])
        elif '- port: 443' in line:
            newfile.append('#    - port: 443')
            newfile.append('#      proto: tcp')
            newfile.append('#      groups:')
            newfile.append('#        - laptop')
            newfile.append('#        - home')
            break
        else:
            newfile.append(line)

    # Write new config to file
    with open(client_ip.split('/')[0] + '-' + client_name + '.yml', 'w') as f:
        for x in range(0, len(newfile)):
            if x < len(newfile) - 1:
                f.write("{}\n".format(newfile[x]))
            else:
                f.write("{}".format(newfile[x]))


def read_template(filename):
    my_list = list()
    with open(filename) as f:
        for line in f:
            if "#" not in line and len(line.strip()) > 0:
                my_list.append(line.split("\n")[0])
    return my_list


def make_ca_certs(my_platform, ca_name):
    if not os.path.isfile('ca.crt') or not os.path.isfile('ca.key'):
        try:
            os.remove("ca.crt")
        except OSError as err:
            print("OS error: {0}".format(err))
        try:
            os.remove("ca.key")
        except OSError as err:
            print("OS error: {0}".format(err))

        print("Creating new CA")
        if my_platform == "windows":
            subprocess.run(["nebula-cert.exe", "ca", "-duration", "87600h0m0s", "-name", ca_name])
            subprocess.run(["nebula-cert.exe", "print", "-path", "ca.crt"])
        if my_platform == "linux":
            subprocess.run(["./nebula-cert", "ca", "-duration", "87600h0m0s", "-name", ca_name])
            subprocess.run(["./nebula-cert", "print", "-path", "ca.crt"])


def make_certs(my_platform, name, ip, subnets, groups):
    if not os.path.isfile(name + '.crt') or not os.path.isfile(name + '.key'):
        try:
            os.remove(name + '.crt')
        except OSError as err:
            print("OS error: {0}".format(err))
        try:
            os.remove(name + '.key')
        except OSError as err:
            print("OS error: {0}".format(err))

        if my_platform == "windows":
            args = ["nebula-cert.exe", "sign", "-name", str(name), "-ip", str(ip)]
            args_print = ["nebula-cert.exe", "print", "-path", name + '.crt']
        if my_platform == "linux":
            args = ["./nebula-cert", "sign", "-name", str(name), "-ip", str(ip)]
            args_print = ["./nebula-cert", "print", "-path", name + '.crt']
        if len(subnets) > 0:
            subnet_var = ','.join(subnets)
            args.append("-subnets")
            args.append(subnet_var)
        if len(groups) > 0:
            groups_var = ','.join(groups)
            args.append("-groups")
            args.append(groups_var)
        print(args)
        subprocess.run(args)

    elif os.path.isfile(name + '.crt') and os.path.isfile(name + '.key'):
        if my_platform == "windows":
            args = ["nebula-cert.exe", "verify", "-ca", "ca.crt", "-crt", name + '.crt']
            args_print = ["nebula-cert.exe", "print", "-path", name + '.crt']
        if my_platform == "linux":
            args = ["./nebula-cert", "verify", "-ca", "ca.crt", "-crt", name + '.crt']
            args_print = ["./nebula-cert", "print", "-path", name + '.crt']
        try:
            subprocess.check_output(args)
            print(name + ".crt matches current CA.")
        except subprocess.CalledProcessError as grepexc:
            print("error code", grepexc.returncode)

    else:
        print("This shouldn't really happen")
    subprocess.run(args_print)


if __name__ == '__main__':
    main()
