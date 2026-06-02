# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure("2") do |config|

  # Base box - Ubuntu 22.04 LTS
  config.vm.box = "ubuntu/jammy64"

  # Disable default synced folder to avoid Windows symlink issues
  config.vm.synced_folder ".", "/vagrant", disabled: true

  # Share only the app and scripts folders (no symlinks needed)
  config.vm.synced_folder "./app",     "/opt/app",     type: "virtualbox"
  config.vm.synced_folder "./scripts", "/opt/scripts", type: "virtualbox"

  # ─────────────────────────────────────────────
  # VM 1: Broker (Redis)
  # ─────────────────────────────────────────────
  config.vm.define "vm-broker" do |broker|
    broker.vm.hostname = "vm-broker"
    broker.vm.network "private_network", ip: "192.168.56.10"

    broker.vm.provider "virtualbox" do |vb|
      vb.name   = "os-lab-broker"
      vb.memory = "512"
      vb.cpus   = 1
    end

    broker.vm.provision "shell", path: "provisioning/broker.sh"
  end

  # ─────────────────────────────────────────────
  # VM 2: Worker (Python workers)
  # ─────────────────────────────────────────────
  config.vm.define "vm-worker" do |worker|
    worker.vm.hostname = "vm-worker"
    worker.vm.network "private_network", ip: "192.168.56.11"

    worker.vm.provider "virtualbox" do |vb|
      vb.name   = "os-lab-worker"
      vb.memory = "512"
      vb.cpus   = 1
    end

    worker.vm.provision "shell", path: "provisioning/worker.sh"
  end

  # ─────────────────────────────────────────────
  # VM 3: Database (PostgreSQL)
  # ─────────────────────────────────────────────
  config.vm.define "vm-db" do |db|
    db.vm.hostname = "vm-db"
    db.vm.network "private_network", ip: "192.168.56.12"

    db.vm.provider "virtualbox" do |vb|
      vb.name   = "os-lab-db"
      vb.memory = "512"
      vb.cpus   = 1
    end

    db.vm.provision "shell", path: "provisioning/db.sh"
  end

end
