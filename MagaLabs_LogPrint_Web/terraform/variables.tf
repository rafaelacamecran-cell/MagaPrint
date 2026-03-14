variable "kube_context" {
  description = "The Kubernetes context to use (e.g., minikube, kind-kind)"
  type        = string
  default     = "minikube"
}
