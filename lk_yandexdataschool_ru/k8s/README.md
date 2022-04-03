```
kubectl apply -f ./namespaces.yaml
kubectl apply -f ./resourcequoata.yaml
pip install k8s-handle
pip install Jinja2==3.1.1
env BACKEND_BUILD_NUMBER=<GITHUB_BUILD_ID> k8s-handle deploy -s prod --use-kubeconfig --sync-mode --strict
```


### How to manage secrets
```
# Create lockbox secret with 'lk.yandexdataschool.ru' name
yc iam service-account create --name yds-secrets-manager
yc iam key create --service-account-name yds-secrets-manager --output authorized-key.json
# Create secret with auth key data in the namespace of the secret store
kubectl config set-context --current --namespace=yds-prod
kubectl create secret generic yc-auth --from-file=authorized-key=authorized-key.json
# Bind service account to the lockbox secret
yc lockbox secret add-access-binding --name "lk.yandexdataschool.ru" --service-account-name yds-secrets-manager --role lockbox.payloadViewer
# And to the shared lockbox
yc lockbox secret add-access-binding --name lms-shared --service-account-name yds-secrets-manager --role lockbox.payloadViewer
# Check bindings
yc lockbox secret list-access-bindings --name lk.yandexdataschool.ru
yc lockbox secret list-access-bindings --name lms-shared
```



Cheat sheet

```
# Set default namespace
kubectl config set-context --current --namespace=yds-prod
# Load data
cat ./sites.json | kubectl exec --stdin website-backend-5d55dfc6f5-qvpkv -c django -- ./manage.py loaddata --format=json -
```
