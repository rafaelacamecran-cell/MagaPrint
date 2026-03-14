terraform {
  required_providers {
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = ">= 2.0.0"
    }
  }
}

provider "kubernetes" {
  config_path    = "~/.kube/config"
  config_context = var.kube_context
}

resource "kubernetes_deployment" "logprint" {
  metadata {
    name = "magalabs-logprint"
    labels = {
      app = "magalabs-logprint"
    }
  }

  spec {
    replicas = 2
    selector {
      match_labels = {
        app = "magalabs-logprint"
      }
    }

    template {
      metadata {
        labels = {
          app = "magalabs-logprint"
        }
      }
      spec {
        container {
          name  = "magalabs-logprint"
          image = "magalabs-logprint:latest"
          image_pull_policy = "IfNotPresent"

          port {
            container_port = 5000
          }

          env {
            name  = "FLASK_APP"
            value = "app.py"
          }
          env {
            name  = "DATABASE_URL"
            value = "postgresql+pg8000://postgres:R%40f%4008049226*%23@host.minikube.internal:5432/MagaLabsLogPrint"
          }
          env {
            name  = "SECRET_KEY"
            value = "magalabs_k8s_secret"
          }

          resources {
            limits = {
              cpu    = "500m"
              memory = "512Mi"
            }
            requests = {
              cpu    = "200m"
              memory = "256Mi"
            }
          }
        }
      }
    }
  }
}

resource "kubernetes_service" "logprint_svc" {
  metadata {
    name = "magalabs-logprint-svc"
  }

  spec {
    selector = {
      app = "magalabs-logprint"
    }
    type = "NodePort"
    port {
      port        = 80
      target_port = 5000
      node_port   = 30000
    }
  }
}
