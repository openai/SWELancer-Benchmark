packer {
  required_plugins {
    azure = {
      source  = "github.com/hashicorp/azure"
      version = "~> 2"
    }
  }
}

source "azure-arm" "example" {
  use_azure_cli_auth = true
  subscription_id                   = "f77ebf0b-8875-4050-b702-696473d0468f"
  managed_image_resource_group_name = "alcatraz-swarm"
  managed_image_name                = "SwarmUbuntu-v61"
  os_type                           = "Linux"
  image_publisher                   = "Canonical"
  image_offer                       = "0001-com-ubuntu-server-jammy"
  image_sku                         = "22_04-lts-gen2"
  location = "northcentralus"
  vm_size  = "Standard_NC4as_T4_v3"
}

build {
  sources = [
    "source.azure-arm.example"
  ]

  provisioner "file" {
    source = "worker.py"
    destination = "/tmp/"
  }

  provisioner "file" {
    source = "worker-systemd"
    destination = "/tmp/"
  }

  provisioner "shell" {
    inline = [
      "sudo apt-get update",

      # python
      "sudo apt-get install -y software-properties-common",
      "sudo add-apt-repository -y ppa:deadsnakes/ppa",
      "sudo apt-get update",
      "sudo apt-get install -y python3.11 python3.11-venv python3.11-dev",
      "sudo ln -s /usr/bin/python3.11 /usr/bin/python",
      "sudo python -m ensurepip",
      "sudo python -m pip install --upgrade pip",

      # docker
      "sudo echo cait",
      "sudo apt-get install -y docker.io",
      "sudo systemctl start docker",
      "sudo systemctl enable docker",

      # NVIDIA GPU drivers (assuming Ubuntu 20.04 or 22.04)
      "sudo apt-get install -y ubuntu-drivers-common",
      "sudo ubuntu-drivers autoinstall",

      # NVIDIA Container Toolkit (even though we install GPU stuff here, VMs without GPUs still work fine so we can have one VM image for GPU and non GPU VMs)
      "curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg",
      "curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list",
      "sudo apt-get update",
      "sudo apt-get install -y nvidia-container-toolkit",
      "sudo nvidia-ctk runtime configure --runtime=docker",
      "sudo systemctl restart docker",

      # azure
      "sudo echo jinx",
      "curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash",
      "sudo echo catchmeifyoucan",
      "sudo useradd -m -s /bin/bash azureuser",
      "sudo usermod -aG docker azureuser",

      # worker
      "sudo mkdir /code",
      "sudo mv /tmp/worker.py /code/worker.py",
      "sudo mv /tmp/worker-systemd /etc/systemd/system/worker.service",
      # installs to azureuser user so we need to add azureuser libs to python path in systemd since systemd runs our worker service as root. for some reason sudo here causes VM to not start, preventing us from using the root users python package location
      "sudo -u azureuser python -m pip install fastapi pydantic==2.7.2 azure-identity azure-keyvault-secrets docker==6.1 pillow tenacity backoff==2.2.1 filelock jupyter-client==8.6 requests==2.31 asyncvnc vncdotool typing-extensions==4.10.0",
      "sudo systemctl daemon-reload",
      "sudo systemctl enable worker.service",

      # preloaded docker images (only works with public images for now)
      "sudo docker pull quay.io/jupyter/base-notebook:python-3.11",
      "sudo docker pull alpine/socat",

      # final checks
      "sudo docker --version",
      "sudo python --version",
    ]
  }
}
