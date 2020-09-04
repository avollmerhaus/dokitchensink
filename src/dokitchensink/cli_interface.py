"""dokitchensink CLI"""

import sys
import time
import argparse
import logging

from dokitchensink.apiwrapper import apiwrapper

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(name)s: %(message)s',
                    handlers=[logging.StreamHandler(sys.stdout)])


def drain():
    logger = logging.getLogger('drain')

    parser = argparse.ArgumentParser(description='dokitchensink sink')
    parser.add_argument('--token', metavar='123456', type=str, required=True, help='DO API token')
    parser.add_argument('--name', metavar='my_funky_droplet', type=str, required=True, help='DO droplet name')

    parser.add_argument('--pub-domain', dest='pub_domain_name', metavar='infra.example.com', type=str, required=True,
                        help='public-facing domain for record removal')

    parser.add_argument('--vpc-domain', dest='vpc_domain_name', metavar='dointern.example.com', type=str,
                        required=False, default=None, help='vpc-facing domain name for record removal')

    parser.add_argument('--force', dest='force', action='store_true', required=False, default=False,
                        help='delete droplets without asking nicely')

    cliargs = parser.parse_args()

    cli_drain = apiwrapper(cliargs.token)

    logger.info(f'{cliargs.name}: deleting all droplets by this name')
    for droplet in cli_drain.get_droplets_by_name(cliargs.name):
        if not cliargs.force:
            orly_del_droplet = input(f'found droplet {droplet.name} with DO id {droplet.id}, delete? (Y/n): ')
        if cliargs.force or orly_del_droplet in ['', 'y', 'Y']:
            droplet.destroy()
            logger.info(f'{cliargs.name}: deleted droplet with DO id {droplet.id}')

    for domain in [cliargs.pub_domain_name, cliargs.vpc_domain_name]:
        # cliargs.vpc_domain_name might be None if not given on the command line
        if domain is not None:
            logger.info(f'{cliargs.name}: deleting all A & AAAA records in domain {domain}')
            for record in cli_drain.get_dns_records_by_name(name=cliargs.name, dns_domain=domain):
                if record.type in ['A', 'AAAA']:
                    if not cliargs.force:
                        orly_del_record = input(f'{cliargs.name}: found record with DO id {record.id}, delete? (Y/n): ')
                    if cliargs.force or orly_del_record in ['', 'y', 'Y']:
                        record.destroy()
                        logger.info(f'{cliargs.name}: deleted record, DO id {record.id}')
                else:
                    logger.warn(f'{cliargs.name}: ignored unexpected {record.type} record in domain {domain}!')


def faucet():
    logger = logging.getLogger('faucet')

    parser = argparse.ArgumentParser(description='dokitchensink faucet')
    parser.add_argument('--token', metavar='123456', type=str, required=True, help='DO API token')
    parser.add_argument('--name', metavar='my_funky_droplet', type=str, required=True, help='DO droplet name')

    parser.add_argument('--pub-domain', dest='pub_domain_name', metavar='infra.example.com', type=str, required=True,
                        help='public-facing domain name for your droplet')

    parser.add_argument('--vpc-domain', dest='vpc_domain_name', metavar='dointern.example.com', type=str,
                        required=False, default=None, help='vpc-facing domain name')

    parser.add_argument("--ssh-key-names", dest='ssh_key_names', metavar='my_key_name', action="extend", nargs="+",
                        type=str, required=True, help='Names of the SSH keys to preseed the droplet with')

    parser.add_argument('--slug', dest='do_size_slug', metavar='s-1vcpu-1gb', type=str, required=False,
                        default='s-1vcpu-1gb', help='DO droplet size slug')

    parser.add_argument('--image', dest='do_image_slug', metavar='centos-8-x64', type=str, required=False,
                        default='centos-8-x64', help='DO droplet image slug')

    parser.add_argument('--region', dest='do_region_slug', metavar='fra1', type=str, required=False,
                        default='fra1', help='DO droplet region slug')

    parser.add_argument("--tags", dest='tag_names', metavar='my_tag', action="extend", nargs="+",
                        type=str, required=False, help='DO tags to tag the droplet with')

    parser.add_argument('--project', dest='do_project_name', metavar='my_do_project', type=str, required=False,
                        default=None, help='DO project name')


    cliargs = parser.parse_args()

    if cliargs.do_project_name:
        raise NotImplementedError(
            'Project support is waiting for https://github.com/koalalorenzo/python-digitalocean/issues/318')

    cli_faucet = apiwrapper(cliargs.token)

    do_ssh_keys = cli_faucet.get_do_ssh_keys_by_name(cliargs.ssh_key_names)
    logger.info(f'got ssh key handles from DO: {do_ssh_keys}')

    droplet = cli_faucet.create_droplet(name=cliargs.name,
                                        do_region=cliargs.do_region_slug,
                                        do_image_slug=cliargs.do_image_slug,
                                        do_size_slug=cliargs.do_size_slug,
                                        do_ssh_keys=do_ssh_keys)

    while not (droplet.ip_address and droplet.ip_v6_address):
        droplet.load()
        logger.info(f'{cliargs.name}: waiting for ip addresses')
        time.sleep(1)

    logger.info(
        f'{cliargs.name}: got ips: {droplet.ip_address}, {droplet.ip_v6_address}, {droplet.private_ip_address}')

    if cliargs.tag_names:
        logger.info(f'{cliargs.name}: set tags: {cliargs.tag_names}')
        cli_faucet.tag_droplet(droplet, cliargs.tag_names)

    for domain in [cliargs.pub_domain_name, cliargs.vpc_domain_name]:
        # cliargs.vpc_domain_name might be None if not given on the command line
        if domain is not None:
            for record in cli_faucet.get_dns_records_by_name(name=cliargs.name, dns_domain=domain):
                if record.type in ['A', 'AAAA']:
                    record.destroy()
                    logger.info(f'{cliargs.name}: deleted obsolete record, DO id {record.id}')
                else:
                    logger.warn(f'{cliargs.name}: ignored unexpected {record.type} record in domain {domain}!')

    new_records = [
        [cliargs.pub_domain_name, 'A', droplet.ip_address],
        [cliargs.pub_domain_name, 'AAAA', droplet.ip_v6_address],
        [cliargs.vpc_domain_name, 'A', droplet.private_ip_address]
    ]
    for domain, type, data in new_records:
        # cliargs.vpc_domain_name might be None if not given on the command line
        if domain is not None:
            logger.info(f'{cliargs.name}: creating {type} record in domain {domain}, {data}')
            cli_faucet.create_dns_record(name=cliargs.name, dns_domain=domain, type=type, data=data)
