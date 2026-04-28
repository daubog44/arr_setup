#!/bin/sh

MAINTENANCE_K3S_TEMPLATE_NAME="Rolling OS Update - K3s Nodes"
MAINTENANCE_K3S_PLAYBOOK_PATH="HaaC/ansible/maintenance-k3s-playbook.yml"
MAINTENANCE_K3S_TEMPLATE_DESCRIPTION="Aggiorna i nodi K3s (serial: 1) ogni lunedi notte"
MAINTENANCE_K3S_SCHEDULE_NAME="Weekly Rolling OS Update - K3s Nodes"
MAINTENANCE_K3S_SCHEDULE_CRON="0 2 * * 1"

MAINTENANCE_PROXMOX_TEMPLATE_NAME="Rolling OS Update - Proxmox Hosts"
MAINTENANCE_PROXMOX_PLAYBOOK_PATH="HaaC/ansible/maintenance-proxmox-playbook.yml"
MAINTENANCE_PROXMOX_TEMPLATE_DESCRIPTION="Aggiorna gli host Proxmox (serial: 1) ogni lunedi notte"
MAINTENANCE_PROXMOX_SCHEDULE_NAME="Weekly Rolling OS Update - Proxmox Hosts"
MAINTENANCE_PROXMOX_SCHEDULE_CRON="30 2 * * 1"

MAINTENANCE_RESTORE_TEMPLATE_NAME="Restore K3s Database (from NAS)"
MAINTENANCE_RESTORE_PLAYBOOK_PATH="HaaC/ansible/restore-k3s-playbook.yml"
MAINTENANCE_RESTORE_TEMPLATE_DESCRIPTION="Restore the SQLite database from NAS to the master node. Use with care. Optional BACKUP_FILE parameter (example: BACKUP_FILE=k3s-state-2023.db)."

MAINTENANCE_SMOKE_TEMPLATE_NAME="HaaC Smoke - Ping Nodes"
MAINTENANCE_SMOKE_PLAYBOOK_PATH="HaaC/ansible/smoke-ping-playbook.yml"
MAINTENANCE_SMOKE_TEMPLATE_DESCRIPTION="Read-only smoke check that verifies Semaphore can reach the managed Ansible targets. It does not upgrade, reboot, or mutate infrastructure."
