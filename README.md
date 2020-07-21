# nebula-config-manager
Creates basic Nebula config files with embedded certificates

### Tool for Nebula VPN:  https://github.com/slackhq/nebula

This scrips tries to simplify nebula config and certificate files. 
When running the script in an empty folder, it will download the windows or linux (amd64)  binary files from the official github repo. It will also grab the templace config file. 

It will then create a new CA if none is found and start issuing node certificates as requested.
The key is that the output is a single config file as I am too lazy to move 4 files to every node manually (ca.crt, node.crt, node,key and config.yml). In this case the certificates are embedded in the config file.

Here is an example:
Download the python script into an empty folder. Open the file in your facorite editor and edit the variables at the top of the file. 

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

Once adjusted to your liking, the first node can be created with:

`python3 generator.py -name lighthouse.nebula -ip 192.168.22.1/24 -groups red,blue -lighthouse true`

This will create a file named: 192.168.22.1-lighthouse.nebula.yml which is now the first lighthouse node and can be started with:  sudo ./nebula -config 192.168.22.1-lighthouse.nebula.yml for example.

To add nodes, the script can be run again like this: 

`python3 generator.py -name client1.nebula -groups red,blue`

It will evaluate the existsing and reserved IP addresses and assign the next available one. (In this case .11)

The script does not adjust any of the default security settings, however the options for the certificates are available. 

    python3 generator.py -h
    Platform is: linux
    usage: generator.py [-h] -name NAME [-ip IP] [-subnets SUBNETS] [-groups GROUPS] [-lighthouse LIGHTHOUSE]
    
    Optional app description
    
    optional arguments:
      -h, --help            show this help message and exit
      -name NAME            specify the name for the new node
      -ip IP                specify the IP for the new node
      -subnets SUBNETS      specify the subnets for the new node)
      -groups GROUPS        specify the groups for the new node)
      -lighthouse LIGHTHOUSE
                            Set to True if this node is a lighthouse.)
    
