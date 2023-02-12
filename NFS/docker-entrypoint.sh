#!/bin/bash

NFS_DIR="/mnt/nfs_share"
IP_MASK="*"

function printBashUsage {
  echo "This script will start the NFS server."
  echo "Usage:"
  echo "-h  | --help: display this message"
  echo "-d  | --dir: path to directory to mount. Default: $NFS_DIR"
  echo "-m  | --ip-mask: mask for the client ip that can connect to the nfs server. Default: ${IP_MASK}"
}

# load config arguments in one line
ARGS=()
while [ ! -z "$1" ]; do
    for v in $1; do
        ARGS+=($v)
    done
    shift 1;
done

# parse arguments
i=0
while [ ! -z ${ARGS[${i}]} ]; do
  case ${ARGS[${i}]} in
    -h|--help) printBashUsage
      exit 0;;
   -d | --dir) NFS_DIR=${ARGS[((i+1))]}; ((i+=2));;
   -m | --ip-mask) IP_MASK=${ARGS[((i+1))]}; ((i+=2));;
   *) echo "Option unknown: ${ARGS[${i}]}."; exit 1;;
  esac
done

echo "$NFS_DIR $IP_MASK(rw,fsid=0,no_subtree_check,no_root_squash)" >> /etc/exports

systemctl enable --now rpcbind
systemctl enable --now nfs-server
exportfs -ar

while :; do sleep 2073600; done
