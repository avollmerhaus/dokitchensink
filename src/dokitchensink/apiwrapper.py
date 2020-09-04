import digitalocean


class apiwrapper:

    def __init__(self, token):
        self.do_token = token
        self.do_api_manager = digitalocean.Manager(token=self.do_token)
        # FIXME: re-add project capability when https://github.com/koalalorenzo/python-digitalocean/issues/318 is fixed
        # self._all_projects = self.do_account_manager.get_all_projects()

    def get_do_ssh_keys_by_name(self, ssh_key_names):
        if isinstance(ssh_key_names, str):
            ssh_key_names = [ssh_key_names]
        do_ssh_keys = [key for key in self.do_api_manager.get_all_sshkeys() if key.name in ssh_key_names]
        if len(do_ssh_keys) != len(ssh_key_names):
            raise ValueError('DO API returned too few or to many ssh key instances for your ssh key names')
        return do_ssh_keys

    def get_droplets_by_name(self, name):
        for droplet in self.do_api_manager.get_all_droplets():
            if droplet.name == name:
                yield droplet

    def get_dns_records_by_name(self, name, dns_domain):
        do_domain = digitalocean.Domain(token=self.do_token, name=dns_domain)
        for record in do_domain.get_records():
            if record.name == name:
                yield record

    def create_dns_record(self, name, dns_domain, type, data, ttl=600):
        do_domain = digitalocean.Domain(token=self.do_token, name=dns_domain)
        do_domain.create_new_domain_record(name=name, type=type, data=data, ttl=ttl)

    def create_droplet(self, name, do_region, do_image_slug, do_size_slug, do_ssh_keys):
        # FIXME: what if a droplet already exists? rebuild it? ask the user about that?
        droplet = digitalocean.Droplet(token=self.do_token,
                                       name=name,
                                       region=do_region,
                                       image=do_image_slug,
                                       size_slug=do_size_slug,
                                       backups=False,
                                       ipv6=True,
                                       private_networking=True,
                                       monitoring=True,
                                       ssh_keys=do_ssh_keys
                                       )
        droplet.create()
        return droplet

    def tag_droplet(self, droplet, tag_names):
        if isinstance(tag_names, str):
            tag_names = [tag_names]
        for tag_name in tag_names:
            tag = digitalocean.Tag(token=self.do_token, name=tag_name)
            tag.create()
            tag.add_droplets(str(droplet.id))

    # def delete_dns_records(self, name, dns_domain, type):
    #     do_domain = digitalocean.Domain(token=self.do_token, name=dns_domain)
    #     existing_records = do_domain.get_records()
    #     [record.destroy() for record in existing_records if record.name == name and record.type == type]

    # def upsert_dns_record(self, name, dns_domain, type, data, ttl=600):
    #     self.delete_dns_records(name, dns_domain, type)
    #     do_domain = digitalocean.Domain(token=self.do_token, name=dns_domain)
    #     do_domain.create_new_domain_record(name=name, type=type, data=data, ttl=ttl)
