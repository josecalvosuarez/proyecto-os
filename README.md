# OS Troubleshooting Lab 🔧

**Sistemas Operativos — Práctica de Troubleshooting**

En este laboratorio trabajarás con un sistema distribuido real corriendo en 3
máquinas virtuales. El sistema tiene **5 problemas de rendimiento** ocultos que
deberás identificar y corregir usando herramientas estándar de Linux.

---

## Arquitectura del sistema

```
┌─────────────────────────────────────────────────────────────┐
│  HOST (Windows)                                             │
│  scripts/load_test.py  ──push jobs──►  vm-broker           │
│  scripts/check_status.py             (Redis queue)         │
└─────────────────────────────┬───────────────────────────────┘
                              │ private network 192.168.56.0/24
          ┌───────────────────┼───────────────────┐
          │                   │                   │
   192.168.56.10       192.168.56.11       192.168.56.12
   vm-broker           vm-worker           vm-db
   Redis 6379          Python workers      PostgreSQL 5432
                       systemd service
```

**Flujo de datos:**
1. El script `load_test.py` empuja jobs a la cola de Redis (vm-broker)
2. Los workers en vm-worker consumen la cola y procesan cada job
3. Los resultados se guardan en PostgreSQL (vm-db)

---

## Requisitos previos

Instala los siguientes programas en tu máquina Windows antes de empezar:

| Herramienta | Descarga | Versión mínima |
|---|---|---|
| VirtualBox | https://www.virtualbox.org/wiki/Downloads | 6.1+ |
| Vagrant | https://developer.hashicorp.com/vagrant/downloads | 2.3+ |
| Python 3 | https://www.python.org/downloads/ | 3.8+ |
| Git | https://git-scm.com/download/win | cualquiera |

> ⚠️ **Importante:** Instala VirtualBox **antes** de Vagrant. Reinicia tu
> máquina después de instalar VirtualBox.

---

## Parte 1 — Levantando el laboratorio

### Paso 1: Clonar el repositorio

Abre **PowerShell** o **Git Bash** y ejecuta:

```powershell
git clone https://github.com/josecalvosuarez/proyecto-os
cd os-troubleshooting-lab
```

### Paso 2: Levantar las máquinas virtuales

```powershell
vagrant up
```

Este proceso descarga la imagen base de Ubuntu y provisiona las 3 VMs.
**Puede tardar 5–15 minutos** la primera vez (descarga ~500 MB).

Verifica que las 3 VMs estén corriendo:

```powershell
vagrant status
```

Deberías ver:

```
vm-broker    running (virtualbox)
vm-worker    running (virtualbox)
vm-db        running (virtualbox)
```

### Paso 3: Instalar dependencias en el host

```powershell
pip install redis psycopg2-binary
```

---

## Parte 2 — Verificando que el sistema funciona (sin carga)

Antes de generar carga, verifica que los tres servicios están activos.

### Verificar Redis (vm-broker)

```powershell
vagrant ssh vm-broker
```

Dentro de la VM:

```bash
# Ver el proceso de Redis
ps aux | grep redis

# Ver uso de memoria del sistema
free -m

# Ver el log de Redis
sudo tail -f /var/log/redis/redis-server.log

# Verificar que Redis responde
redis-cli ping        # debe responder: PONG

# Ver información de Redis
redis-cli INFO server | grep redis_version
redis-cli INFO memory | grep used_memory_human

# Salir de la VM
exit
```

### Verificar el worker (vm-worker)

```powershell
vagrant ssh vm-worker
```

Dentro de la VM:

```bash
# Ver el proceso del worker
ps aux | grep python

# Ver el estado del servicio systemd
systemctl status worker

# Ver uso de CPU y memoria en tiempo real
top

# (presiona Q para salir de top)

# Ver uso del disco
df -h

# Salir de la VM
exit
```

### Verificar PostgreSQL (vm-db)

```powershell
vagrant ssh vm-db
```

Dentro de la VM:

```bash
# Ver el proceso de PostgreSQL
ps aux | grep postgres

# Conectarse a la base de datos
psql -U labuser -d labdb -h localhost

# Dentro de psql:
\dt                          -- listar tablas
SELECT COUNT(*) FROM jobs;   -- debe ser 0
\q                           -- salir de psql

# Ver uso de memoria
free -m

# Salir de la VM
exit
```

### Verificar el sistema completo

Desde PowerShell en tu host:

```powershell
python scripts/check_status.py
```

Deberías ver algo así cuando todo está sano:

```
        OS TROUBLESHOOTING LAB — SYSTEM STATUS
  2024-01-15 10:32:01
----------------------------------------------------
         BROKER (vm-broker — 192.168.56.10)
----------------------------------------------------
  Status        : OK
  Queue depth   : 0 jobs pending
  Memory used   : 0.8 MB / 8.0 MB max
  Memory usage  : [####----------------] 10%

          DATABASE (vm-db — 192.168.56.12)
----------------------------------------------------
  Status        : OK
  Jobs pending  : 0
  Jobs done     : 0
  Results saved : 0
  Connections   : 1 active
  Throughput    : no results in last 1 minute
```

---

## Parte 3 — Generando carga

### Paso 1: Lanzar el generador de carga

Abre una **nueva ventana de PowerShell** (mantén las VMs corriendo) y ejecuta:

```powershell
python scripts/load_test.py
```

Verás una salida como esta:

```
OS Troubleshooting Lab — Load Generator
----------------------------------------
Target : Redis @ 192.168.56.10:6379
Queue  : job_queue
Rate   : 10 jobs/sec  |  Payload: large (50000 chars)

Conectando a Redis...
Conectado. Starting load... (Ctrl+C to stop)

[10:33:15] Pushed:     50 jobs | Queue depth:    47 | Rate:   9.8 jobs/s | Redis mem: 4.2 MB
```

### Paso 2: Monitorear en tiempo real

Con el generador corriendo, abre **otra ventana de PowerShell** y corre:

```powershell
python scripts/check_status.py
```

Ejecuta este comando cada 30–60 segundos para ver cómo evoluciona el sistema.

---

## Parte 4 — Troubleshooting

A partir de este punto el sistema comenzará a mostrar síntomas de problemas.

Tu tarea es:

1. **Observar** los síntomas (¿qué va mal? ¿qué dice `check_status.py`?)
2. **Conectarte a las VMs** con `vagrant ssh vm-broker`, `vm-worker` o `vm-db`
3. **Usar las herramientas de monitoreo** para identificar el proceso culpable
4. **Identificar la causa raíz** en la configuración o el código
5. **Aplicar el fix** y verificar que el síntoma desaparece

### Herramientas que deberás usar

| Herramienta | Qué muestra | Ejemplo |
|---|---|---|
| `ps aux` | Todos los procesos con CPU y memoria | `ps aux --sort=-%cpu` |
| `top` | Procesos en tiempo real | `top` (Q para salir) |
| `free -m` | Memoria RAM disponible | `free -m` |
| `df -h` | Espacio en disco por partición | `df -h` |
| `vmstat 1` | CPU, memoria, I/O por segundo | `vmstat 1 10` |
| `ss -tnp` | Conexiones de red activas | `ss -tnp` |
| `journalctl` | Logs del sistema | `journalctl -u worker -f` |
| `du -sh` | Tamaño de directorios | `du -sh /var/log/*` |

### Pistas de síntomas (sin spoilers)

Los síntomas que verás se manifiestan en las métricas de `check_status.py` y
en las herramientas de monitoreo dentro de las VMs. Algunos aparecen rápido,
otros tardan unos minutos en desarrollarse.

**No hay un orden fijo** — usa lo que observas para decidir por dónde empezar.

---

## Comandos útiles de Vagrant

```powershell
vagrant status              # ver estado de las VMs
vagrant ssh vm-broker       # entrar a una VM
vagrant halt                # apagar todas las VMs
vagrant up                  # volver a levantar las VMs
vagrant destroy -f          # eliminar todas las VMs (reset total)
vagrant reload --provision  # reiniciar y re-provisionar (reset al estado inicial)
```

> 💡 **Tip:** Si quieres empezar de cero después de hacer cambios,
> usa `vagrant destroy -f && vagrant up`.

---

## Entregable

Al finalizar el laboratorio deberás entregar un reporte con:

1. Lista de los 5 problemas encontrados
2. Para cada problema:
   - Síntoma observado
   - VM afectada
   - Herramienta(s) usada(s) para identificarlo
   - Proceso o servicio responsable (`ps`/`top` output)
   - Causa raíz (configuración o código)
   - Fix aplicado y evidencia de que funcionó

---

*Sistemas Operativos — Laboratorio de Troubleshooting*
