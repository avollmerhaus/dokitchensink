dokitchensink
===

Manually creating or deleting droplets and associated DNS records for them using the DO website is error-prone and a chore,
especially when creating public A and AAAA records plus another A record for your VPC network.

Digitalocean's own `doctl` is better, but does not combine all steps in one go.
You'd need to get the IPs from `doctl` into some kind of shell script, then use that script to check 
if stray DNS records already exist so you can update instead of insert - assuming a very basic usecase where
you usually don't want multiple records for the same name.

Instead of hapharzardly stringing together some doctl commands using the shell, I decided I'd rather do it in python.
And when doing it in python, why wrap doctl when you can go straight for the DO API.

## Usage

### Create droplet
```shell
dokitchensink-faucet --token foo --name test1 --pub-domain infra.example.com --vpc-domain dointern.example.com --ssh-key-names my_key your_key
```

### Delete droplet
```shell
dokitchensink-drain --token foo --name test1 --pub-domain infra.example.com --vpc-domain dointern.example.com
```

## Installation
Note that your poetry installation needs to run on python3.8 at least.

```shell
cd dokitchensink
poetry install
```

## Notes
- The DO token is exposed in the process list while the scipt is running, so you'll have to trust your local machine.
- dokitchensink-faucet assumes a few things and makes little to no effort to expose these assumptions via the cli:
  - backups: off (I'm assuming droplets are expendable, if not: turn on the backups afterwards)
  - VPC: on
  - monitoring: on
  - ipv6: on
