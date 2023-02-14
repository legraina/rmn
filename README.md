# Reconaissance des matricules et notes

### General information for installation

##### Ingress
nginx is only used as a reverse proxy to redirect all requests to kubernetes and to handle certificates.
All the routing part is handle by ingress (i.e., nginx in kubernetes).

##### Mongo
Mongo is run within the kubernetes cluster now.

##### Firebase
Firebase has been removed and a NFS (run inside the cluster) is instead used to synchronize and share files between containers, as well as persistent storage.

##### KEDA update
Do not use Keda 2.81, instead Keda 2.9.* as Kubernetes 1.20+ is only supported from 2.9:
```
kubectl apply -f https://github.com/kedacore/keda/releases/download/v2.9.3/keda-2.9.3.yaml
```

##### Create first admin user
```
curl -X POST -H "Content-Type:multipart/form-data" --form "username=admin" --form "password=test" --form "role=Administrateur" "http://rmn.mgi.polymtl.ca/api/signup"
```

### Persistent volume: NFS server
WARNING: you need to mount a persistent volume that correspond to the path given to the nfs server, otherwise you will have an error as docker is not able to mount other paths for a nsf server. Furthermore, if using minikube, the path of the persistent volume needs also to be persistent in minikube: you can use a default persistent path like "/data" or any other path that has been mounted in minikube to communicate with the host.

Access to nsf pods from outside
```
kubectl port-forward <nfs pod> :2049
```

You will have an output like this one:
```
Forwarding from 127.0.0.1:42349 -> 2049
Forwarding from [::1]:42349 -> 2049
```

Then, mount the nfs volume:
```
sudo mount -t nfs -o port=42349 127.0.0.1:/ /your/host/path/folder
```

### Modify deployment
Once a deployment yml file has been modified, you need to apply those modifications:
```
kubectl apply -f modified_deployment.yml
```
Then, to ensure the new pods are created, rollout the service for a deployment:
```
kubectl rollout restart deployment <modified deployment>
```
Or delete the corresponding pods for a Replication Controller:
```
kubectl delete pods <modified deployment pod>
```
