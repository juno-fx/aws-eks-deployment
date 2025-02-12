.PHONY: update-tools install lint check format dev dependencies down test

# shell
SHELL := /bin/bash

# runtimes
PYTHON := true
NODE := false
ENV := PYTHON=$(PYTHON) NODE=$(NODE)


# updater
update-tools:
	@ echo " >> Pulling Latest Tools << "
	@ rm -rf Development-Tools
	@ git clone https://github.com/juno-fx/Development-Tools.git
	@ rm -rf .tools
	@ mv -v Development-Tools/.tools .tools
	@ rm -rf Development-Tools
	@ echo " >> Tools Updated << "

.tools/cluster.Makefile:
	@ $(MAKE) update-tools

.tools/dev.Makefile:
	@ $(MAKE) update-tools

# Environment targets
dev: .tools/cluster.Makefile
	@ $(MAKE) -f .tools/cluster.Makefile cluster --no-print-directory
	@ sleep 5
	@ kubectl wait --namespace argocd --for=condition=ready pod --selector=app.kubernetes.io/name=argocd-server --timeout=90s
	@ sleep 5
	@ echo " >> ArgoCD Admin Credentials Below << "
	@ echo "admin"
	@ kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 --decode; echo
	@ echo
	@ echo " >> ArgoCD UI: http://localhost:8080 << "
	@ echo " >> Installing Bootstrap << "
	@ kubectl apply -f bootstrap-app.yaml
	@ kubectl port-forward service/argocd-server -n argocd 8080:80

down: .tools/cluster.Makefile
	@ $(MAKE) -f .tools/cluster.Makefile down --no-print-directory

dependencies:
	@ kubectl create namespace argocd > /dev/null || echo "Namespace already exists"
	@ kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/release-2.13/manifests/install.yaml > /dev/null

