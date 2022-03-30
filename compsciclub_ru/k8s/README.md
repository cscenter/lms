```
kubectl apply -f ./namespaces.yaml
kubectl apply -f ./resourcequoata.yaml
pip install k8s-handle
pip install Jinja2==3.1.1
env BACKEND_BUILD_NUMBER=37 k8s-handle deploy -s prod --use-kubeconfig --strict
```


### How to manage secrets
```
yc iam service-account create --name csclub-secrets-manager
yc iam key create --service-account-name csclub-secrets-manager --output authorized-key.json
# Create secret with auth key data in the namespace of the secret store
kubectl create secret generic yc-auth --from-file=authorized-key=authorized-key.json
# Create lockbox secret with UI or CLI, then bind service account to the lockbox secret
yc lockbox secret add-access-binding --name "compsciclub.ru" --service-account-name csclub-secrets-manager --role lockbox.payloadViewer
# And to the shared lockbox
yc lockbox secret add-access-binding --name lms-shared --service-account-name csclub-secrets-manager --role lockbox.payloadViewer
# Check bindings
yc lockbox secret list-access-bindings --name compsciclub.ru
yc lockbox secret list-access-bindings --name lms-shared
```



Cheat sheet

```
# Set default namespace
kubectl config set-context --current --namespace=
# Load data
cat ./sites.json | kubectl exec --stdin website-backend-5d55dfc6f5-qvpkv -c django -- ./manage.py loaddata --settings=lk_yandexdataschool_ru.settings.production --format=json -
```
