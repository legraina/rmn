Projet 4


Add one user manually
```
curl -X POST -H "Content-Type:multipart/form-data" --form "username=admin" --form "password=test" --form "role=Administrateur" "http://rmn.mgi.polymtl.ca/api/signup"
```

Rollout service:
```
kubectl rollout restart deployment <service>
```

Persistent volume use NFS server
