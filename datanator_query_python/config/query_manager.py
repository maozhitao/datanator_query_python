from datanator_query_python.config import config
from datanator_query_python.query import (query_protein, front_end_query, query_metabolites,
                                         query_sabiork_old, query_taxon_tree)

class Manager:

    def __init__(self):
        self.username = config.Config.USERNAME
        self.password = config.Config.PASSWORD
        self.server = config.Config.SERVER
        self.authDB = config.Config.AUTHDB
        self.read_preference = config.Config.READ_PREFERENCE

    def protein_manager(self):
        return query_protein.QueryProtein(username=self.username, password=self.password, server=self.server,
        authSource=self.authDB, readPreference=self.read_preference)

    def metabolite_manager(self):
        return front_end_query.QueryFrontEnd(username=self.username, password=self.password, MongoDB=self.server,
        authDB=self.authDB, readPreference=self.read_preference)

    def eymdb_manager(self):
        return query_metabolites.QueryMetabolites(
            username=self.username,
            password=self.password,
            MongoDB=self.server,
            authSource=self.authDB,
            db='datanator',
            readPreference=self.read_preference)


class RxnManager:

    def rxn_manager(self):
        return query_sabiork_old.QuerySabioOld(username=config.Config.USERNAME, 
        password=config.Config.PASSWORD, MongoDB=config.Config.SERVER,
        authSource=config.Config.AUTHDB, readPreference=config.Config.READ_PREFERENCE)


class TaxonManager:

    def txn_manager(self):
        return query_taxon_tree.QueryTaxonTree(username=config.Config.USERNAME, 
        password=config.Config.PASSWORD, MongoDB=config.Config.SERVER,
        authSource=config.Config.AUTHDB, readPreference=config.Config.READ_PREFERENCE)
