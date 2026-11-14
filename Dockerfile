# Образ-«терминал» для сборки методички: docker CLI + kubectl, kind, helm, k9s + bash/curl/jq.
# Демон — отдельный (docker:dind), см. tools/build-manual.py и src/run.json
FROM docker:cli
ARG KUBECTL_VERSION=v1.37.0
ARG KIND_VERSION=v0.33.0
ARG HELM_VERSION=v4.3.2
ARG K9S_VERSION=v0.51.0
RUN apk add --no-cache bash curl jq git openssl apache2-utils postgresql18-client bind-tools ca-certificates socat diffutils \
 && A=$(uname -m | sed 's/x86_64/amd64/;s/aarch64/arm64/') \
 && curl -fsSL "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/$A/kubectl" -o /usr/local/bin/kubectl \
 && curl -fsSL "https://kind.sigs.k8s.io/dl/${KIND_VERSION}/kind-linux-$A" -o /usr/local/bin/kind \
 && chmod +x /usr/local/bin/kubectl /usr/local/bin/kind \
 && curl -fsSL "https://get.helm.sh/helm-${HELM_VERSION}-linux-$A.tar.gz" | tar -xz -C /tmp && mv /tmp/linux-$A/helm /usr/local/bin/helm \
 && curl -fsSL "https://github.com/derailed/k9s/releases/download/${K9S_VERSION}/k9s_Linux_$A.tar.gz" | tar -xz -C /usr/local/bin k9s
WORKDIR /work
CMD ["bash"]
