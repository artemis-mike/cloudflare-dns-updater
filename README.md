# Cloudflare DNS Updater
## Synopsis
A script that reconciles a Cloudflare DNS A-record against the hosts current public IP address.

## Configuration 

| Variable                  | Description | Default |
|---------------------------|-------------|---------|
| CF_UPDATER_LOGLEVEL       | Python log level (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`) |  `INFO` |
| CF_UPDATER_ZONE_ID        | **Required** DNS Zone ID  in Cloudflare Websites Dashboard | `""` |
| CF_UPDATER_A_RECORD       | **Required** (if not using CF_UPDATER_AAAA_RECORD) Zones DNS A-record to change | `""` |
| CF_UPDATER_AAAA_RECORD    | **Required** (if not using CF_UPDATER_A_RECORD) Zones DNS AAAA-record to change | `""` |
| CF_UPDATER_TOKEN          | **Required** Cloudflare API Token with permissions to change DNS Records | `""` |
| CF_UPDATER_INTERVAL       | Seconds to wait between reconsiliation runs | `30` |
| CF_UPDATER_FORCE_INTERVAL | To stay far away from Cloudflares rate limits, it's not recomended to use a interval of less than 5s. To override this set to `True`. See https://developers.cloudflare.com/fundamentals/api/reference/limits/| `False`|

## Run
Fill a env-file with your details
```
vi .env
```

Run the container
```
docker compose up -d
```

## IPv4 vs IPv6
To be able to set AAAA-rcords, your container needs to work with IPv6. Configure docker daemon to use IPv6 by adding this to `/etc/docker/daemon.json`
```
{
  "ipv6": true,
  "fixed-cidr-v6": "2001:db8:1::/64",
  "ip6tables": true
}
```

## Healthchecks
This image provides **two** healthchecks.  
- `health.sh` for all systems that can handle healthchecks sanely, like Kubernetes, Docker Swarm, etc.  
- `health-compose.sh` is intended for `docker compose`, which currently lacks handling of unhealthy containers. It kills the entrypoint-process once the built-in check fails **once**! This causes PID 1 to get terminated and the container stops.
Depending in the restart-policy (e.g. `restart: always`) the container gets restarted.  
Please be aware, that using `health-compose.sh` renders `healthcheck.retries` useless. PID 1 gets killed if the healthcheck fails once.
