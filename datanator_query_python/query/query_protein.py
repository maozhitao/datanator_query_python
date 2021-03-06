from datanator_query_python.util import mongo_util, file_util
from datanator_query_python.query import query_taxon_tree, query_kegg_orthology
from pymongo.collation import Collation, CollationStrength
from pymongo import ASCENDING
from collections import deque
import simplejson as json


class QueryProtein(mongo_util.MongoUtil):

    def __init__(self, username=None, password=None, server=None, authSource='admin',
                 database='datanator', max_entries=float('inf'), verbose=True, collection_str='uniprot',
                 readPreference='nearest', replicaSet=None):

        super().__init__(MongoDB=server, username=username,
                        password=password, authSource=authSource, db=database,
                        readPreference=readPreference, replicaSet=replicaSet)
        self.taxon_manager = query_taxon_tree.QueryTaxonTree(MongoDB=server, username=username, password=password,
            authSource=authSource, db=database, replicaSet=replicaSet)
        self.taxon_col = self.db_obj['taxon_tree']
        self.kegg_manager = query_kegg_orthology.QueryKO(username=username, password=password, server=server, authSource=authSource, replicaSet=replicaSet)
        self.file_manager = file_util.FileUtil()
        self.max_entries = max_entries
        self.verbose = verbose
        self.collection = self.db_obj[collection_str]
        self.paxdb_collection = self.db_obj['pax']
        self.collation = Collation(locale='en', strength=CollationStrength.SECONDARY)
        self.collection_str = collection_str

    def get_meta_by_id(self, _id):
        '''
            Get protein's metadata given uniprot id

            Args:
                _id (:obj:`list` of :obj:`str`): list of uniprot id.

            Returns:
                (:obj:`list` of :obj:`dict`): list of information.
        '''
        result = []
        query = {'uniprot_id': {'$in': _id}}
        projection = {'_id': 0, 'ancestor_name': 0, 'ancestor_taxon_id': 0,
                    'kinetics': 0}
        docs = self.collection.find(filter=query, projection=projection, collation=self.collation)
        count = self.collection.count_documents(query, collation=self.collation)
        null = 'None'
        if count == 0:
            return {'uniprot_id': 'None',
            'entry_name': 'None',
            'gene_name': 'None',
            'protein_name': 'None',
            'canonical_sequence': 'None',
            'length': 99999999,
            'mass': '99999999',
            'abundances': [],
            'ncbi_taxonomy_id': 99999999,
            'species_name': '99999999'}

        for doc in docs:
            doc = json.loads(json.dumps(doc, ignore_nan=True))
            ko_number = doc.get('ko_number')
            if ko_number is not None:
                D, c = self.kegg_manager.get_meta_by_kegg_ids([ko_number])
                if c != 0:
                    doc['kegg_meta'] = [d for d in D]    
            result.append(doc)
        return result

    def get_ortho_by_id(self, _id):
        '''
            Get protein's metadata given uniprot id

            Args:
                _id (:obj:`str`): uniprot id.

            Returns:
                (:obj:`list` of :obj:`dict`): list of information.
        '''
        result = []
        query = {'uniprot_id': _id}
        doc = self.collection.find_one(filter=query, projection={"_id": 0})
        if doc is None:
            return {'uniprot_id': 'None',
            'entry_name': 'None',
            'gene_name': 'None',
            'protein_name': 'None',
            'canonical_sequence': 'None',
            'length': 99999999,
            'mass': '99999999',
            'abundances': [],
            'ncbi_taxonomy_id': 99999999,
            'species_name': '99999999'}
        else:
            doc = json.loads(json.dumps(doc, ignore_nan=True))
            result.append(doc)
            return result            

    def get_meta_by_name_taxon(self, name, taxon_id):
        '''
            Get protein's metadata given protein name
            and its ncbi taxonomy ID

            Args:
                name (:obj:`str`): protein's complete/partial name.
                taxon_id (:obj:`int`): protein's ncbi taxonomy id.

            Returns:
                (:obj:`list` of :obj:`dict`): protein's metadata.
        '''
        result = []
        expression = "\"" + name + "\""
        query = {'$and': [{'$text': { '$search': expression } },
                         {'ncbi_taxonomy_id': taxon_id},
                         {'abundances': {'$exists': True} }]}
        projection = {'_id': 0, 'ancestor_name': 0, 'ancestor_taxon_id': 0, 'kinetics': 0}
        docs = self.collection.find(filter=query, projection=projection)
        for doc in docs:
            doc = json.loads(json.dumps(doc, ignore_nan=True))
            result.append(doc)
        return result

    def get_meta_by_name_name(self, protein_name, species_name):
        '''
            Get protein metadata by protein name and the 
            name of the species the protein resides

            Args:
                protein_name (:obj:`str`): name of the protein
                species_name (:obj:`str`): complete/partial name of the organism

            Returns:
                (:obj:`list` of :obj:`dict`): protein's metadata
        '''
        result = []
        taxon_ids = self.taxon_manager.get_ids_by_name(species_name)
        expression = "\"" + protein_name + "\""
        query = {'$and': [{'$text': { '$search': expression } },
                         {'ncbi_taxonomy_id': {'$in' :taxon_ids}},
                         {'abundances': {'$exists': True} }]}
        projection = {'_id': 0, 'ancestor_name': 0, 'ancestor_taxon_id': 0, 'kinetics': 0}
        docs = self.collection.find(filter=query, projection=projection)
        for doc in docs:
            doc = json.loads(json.dumps(doc, ignore_nan=True))
            result.append(doc)
        return result

    def get_id_by_name(self, name):
        '''
            Get proteins whose name contains string 'name'.

            Args:
                name (:obj:`str`): complete/incomplete protein name.

            Returns:
                (:obj:`list` of :obj:`dict`): list of dictionary containing 
                protein's uniprot_id and name.
        '''
        result = []
        expression = "\"" + name + "\""
        query = { '$text': { '$search': expression } }
        projection = {'_id': 0, 'uniprot_id': 1, 'protein_name': 1}
        docs = self.collection.find(filter=query, projection=projection)
        # count = self.collection.count_documents(query)
        # if count == 0:
        #     return 'No protein found'
        for doc in docs:
            dic = {'uniprot_id': doc['uniprot_id'], 'protein_name': doc['protein_name']}
            result.append(dic)
        return result

    def get_info_by_text(self, name):
        '''
            Get proteins whose name or kegg name contains string 'name'.

            Args:
                name (:obj:`str`): complete/incomplete protein name.

            Returns:
                (:obj:`list` of :obj:`dict`): list of dictionary containing 
                protein's uniprot_id and kegg information
                [{'ko_number': ... 'ko_name': ... 'uniprot_ids': []},
                 {'ko_number': ... 'ko_name': ... 'uniprot_ids': []}].
        '''
        result = []
        expression = "\"" + name + "\""
        query = { '$text': { '$search': expression } }
        projection = {'_id': 0, 'uniprot_id': 1, 'ko_number': 1, 'ko_name': 1}
        docs = self.collection.find(filter=query, projection=projection)

        for doc in docs:
            ko_number = doc.get('ko_number', 'no number')
            ko_name = doc.get('ko_name', ['no name'])
            uniprot_id = doc['uniprot_id']
            index = self.file_manager.search_dict_index(result, 'ko_number', ko_number)
            if len(index) == 1:
                result[index[0]]['uniprot_ids'].append(uniprot_id)
            else:
                dic = {'ko_number': ko_number, 'ko_name': ko_name, 'uniprot_ids': [uniprot_id]}
                result.append(dic)
        return result

    def get_info_by_text_abundances(self, name):
        '''
            Get proteins whose name or kegg name contains string 'name'.

            Args:
                name (:obj:`str`): complete/incomplete protein name.

            Returns:
                (:obj:`list` of :obj:`dict`): list of dictionary containing 
                protein's uniprot_id and kegg information
                [{'ko_number': ... 'ko_name': ... 'uniprot_ids': {'id0': 0, 'id1': 1, 'id2': 0}}, # 0: has abundances info, 1: no abundances infor
                 {'ko_number': ... 'ko_name': ... 'uniprot_ids': {'id0': 0, 'id1': 1, 'id2': 0}}].
        '''
        result = []
        expression = "\"" + name + "\""
        query = { '$text': { '$search': expression } }
        projection = {'_id': 0, 'uniprot_id': 1, 'ko_number': 1, 'ko_name': 1, 'abundances': 1}
        docs = self.collection.find(filter=query, projection=projection)

        for doc in docs:
            ko_number = doc.get('ko_number')
            ko_name = doc.get('ko_name')
            if ko_number is None or ko_number == 'nan':
                ko_number = 'no number'
                ko_name = ['no name']           
            uniprot_id = doc['uniprot_id']
            abundance_status = 'abundances' in doc
            index = self.file_manager.search_dict_index(result, 'ko_number', ko_number)
            if len(index) == 1:
                result[index[0]]['uniprot_ids'][uniprot_id] = abundance_status
            else:
                dic = {'ko_number': ko_number, 'ko_name': ko_name, 'uniprot_ids': {uniprot_id: abundance_status}}
                result.append(dic)
        return result

    def get_info_by_taxonid(self, _id):
        '''
            Get proteins whose name or kegg name contains string 'name'.

            Args:
                _id (:obj:`int`): ncbi taxonomy id.

            Returns:
                (:obj:`list` of :obj:`dict`): list of dictionary containing 
                protein's uniprot_id and kegg information
                [{'ko_number': ... 'ko_name': ... 'uniprot_ids': []},
                 {'ko_number': ... 'ko_name': ... 'uniprot_ids': []}].
        '''
        result = []
        query = {'ncbi_taxonomy_id': _id}
        projection = {'_id': 0, 'uniprot_id': 1, 'ko_number': 1, 'ko_name': 1}
        docs = self.collection.find(filter=query, projection=projection)

        for doc in docs:
            ko_number = doc.get('ko_number', 'no number')
            ko_name = doc.get('ko_name', ['no name'])
            uniprot_id = doc['uniprot_id']
            index = self.file_manager.search_dict_index(result, 'ko_number', ko_number)
            if len(index) == 1:
                result[index[0]]['uniprot_ids'].append(uniprot_id)
            else:
                dic = {'ko_number': ko_number, 'ko_name': ko_name, 'uniprot_ids': [uniprot_id]}
                result.append(dic)
        return result

    def get_info_by_taxonid_abundance(self, _id):
        '''
            Get proteins associated with ncbi id.

            Args:
                _id (:obj:`int`): ncbi taxonomy id.

            Returns:
                result (:obj:`list` of :obj:`dict`): list of dictionary containing 
                protein's uniprot_id and kegg information
                [{'ko_number': ... 'ko_name': ... 'uniprot_ids': {'id0': 0, 'id1': 1, 'id2': 0}},
                 {'ko_number': ... 'ko_name': ... 'uniprot_ids': {'id0': 0, 'id1': 1, 'id2': 0}}].
        '''
        result = []
        query = {'ncbi_taxonomy_id': _id}
        projection = {'_id': 0, 'uniprot_id': 1, 'ko_number': 1, 'ko_name': 1, 'abundances': 1}
        docs = self.collection.find(filter=query, projection=projection)

        for doc in docs:
            ko_number = doc.get('ko_number', 'no number')
            ko_name = doc.get('ko_name', ['no name'])
            uniprot_id = doc['uniprot_id']
            abundance_status = 'abundances' in doc
            index = self.file_manager.search_dict_index(result, 'ko_number', ko_number)
            if len(index) == 1:
                result[index[0]]['uniprot_ids'][uniprot_id] = abundance_status
            else:
                dic = {'ko_number': ko_number, 'ko_name': ko_name, 'uniprot_ids': {uniprot_id: abundance_status}}
                result.append(dic)
        return result

    def get_info_by_ko(self, ko):
        '''
            Find all proteins with the same kegg orthology id.

            Args:
                ko (:obj:`str`): kegg orthology ID.

            Returns:
                (:obj:`list` of :obj:`dict`): list of dictionary containing 
                protein's uniprot_id and kegg information
                [{'ko_number': ... 'ko_name': ... 'uniprot_ids': []},
                 {'ko_number': ... 'ko_name': ... 'uniprot_ids': []}].
        '''
        ko = ko.upper()
        result = [{'ko_number': ko, 'uniprot_ids': []}]
        query = {'ko_number': ko}
        projection = {'uniprot_id': 1, '_id': 0, 'ko_name': 1, 'ko_number': 1}
        docs = self.collection.find(filter=query, projection=projection)

        for doc in docs:
            result[0]['ko_name'] = doc.get('ko_name', ['no name'])
            result[0]['uniprot_ids'].append(doc.get('uniprot_id'))
        return result

    def get_info_by_ko_abundance(self, ko):
        '''
            Find all proteins with the same kegg orthology id.

            Args:
                ko (:obj:`str`): kegg orthology ID.

            Returns:
                (:obj:`list` of :obj:`dict`): list of dictionary containing 
                protein's uniprot_id and kegg information
                [{'ko_number': ... 'ko_name': ... 'uniprot_ids': {}},
                 {'ko_number': ... 'ko_name': ... 'uniprot_ids': {}}].
        '''
        ko = ko.upper()
        result = [{'ko_number': ko, 'uniprot_ids': {}}]
        query = {'ko_number': ko}
        projection = {'uniprot_id': 1, '_id': 0, 'ko_name': 1, 'ko_number': 1, 'abundances': 1}
        docs = self.collection.find(filter=query, projection=projection)

        for doc in docs:
            result[0]['ko_name'] = doc.get('ko_name', ['no name'])
            abundance_status = 'abundances' in doc
            result[0]['uniprot_ids'][doc.get('uniprot_id')] = abundance_status
        return result

    def get_kinlaw_by_id(self, _id):
        '''
            Get protein kinetic law information by uniprot_id.

            Args:
                _id (:obj:`list` of :obj:`str`): list of uniprot IDs.

            Returns:
                (:obj:`list` of `dict`): list of kinlaw information.
        '''
        result = []
        query = {'uniprot_id': {'$in': _id}}
        projection = {'_id': 0, 'kinetics': 1, 'taxon': 1, 'uniprot_id': 1}
        docs = self.collection.find(filter=query, projection=projection, collation=self.collation)
        for doc in docs:
            result.append({'uniprot_id': doc.get('uniprot_id'), 'ncbi_taxonomy_id': doc.get('taxon'),
                'similar_functions': doc.get('kinetics')})
        return result

    def get_kinlaw_by_name(self, name):
        '''
        Get protein kinetic law information by protein name.

        Args:
            _id: (:obj:`str`): protein's name.

        Returns:
            (:obj:`list` of :obj:`dict`): information.
        '''
        entries = self.get_id_by_name(name)
        _ids = []
        for entry in entries:
            _ids.append(entry['uniprot_id'])
        return self.get_kinlaw_by_id(_ids)

    def get_abundance_by_id(self, _id):
        '''
        	Get protein abundance information by uniprot_id.

        	Args:
				id (:obj:`list` of :obj:`str`): list of uniprot_id.

			Returns:
				(:obj:`list` of `dict`): list of abundance information.
        '''
        result = []
        query = {'$and': [{'uniprot_id': {'$in': _id}}, {'abundances': {'$exists': True}}]}

        projection = {'abundances': 1, 'uniprot_id': 1, '_id': 0,
                      'protein_name': 1, 'gene_name': 1, 'species_name': 1,
                      "modifications": 1}
        docs = self.collection.find(filter=query, projection=projection, collation=self.collation)
        count = self.collection.count_documents(query, collation=self.collation)
        if count == 0:
            return [{'abundances': [], 'uniprot_id': 'No proteins that match input',
                     "species_name": "No proteins that match input"}]
        for doc in docs:
            result.append(doc)
        return result

    def get_abundance_by_taxon(self, _id):
        '''
            Get protein abundance information in one species.

            Args:
                id (:obj:`str`): taxonomy id.

            Returns:
                (:obj:`list` of `dict`): list of abundance information
        '''
        result = []
        query = {'ncbi_taxonomy_id': _id}
        projection = {'ancestor_name': 0, 'ancestor_taxon_id': 0, '_id': 0, 'ncbi_taxonomy_id': 0}
        docs = self.collection.find(filter=query, projection=projection)
        for doc in docs:
            result.append(doc)
        return result

    def get_proximity_abundance_taxon(self, _id, max_distance=3):
        '''
        	Get replacement abundance value by taxonomic distance
        	with the same kegg_orthology number.

            Args:
                _id (:obj:`str`): uniprot_id to query for
                max_distance (:obj:`int`): max taxonomic distance from origin protein allowed for
                                            proteins in results.

            Returns:
                (:obj:`list` of :obj:`dict`): list of result proteins and their info 
                    [{'distance': 1, 'documents': [{}, {}, {} ...]}, 
                     {'distance': 2, 'documents': [{}, {}, {} ...]}, ...]
        '''
        if max_distance == 0:
            return 'Please use get_abundance_by_id to check self abundance values'

        result = []
        for i in range(max_distance):
            result.append({'distance': i + 1, 'documents': []})

        query = {'$and': [{'uniprot_id': _id},
                        {'ancestor_taxon_id': {'$exists': True}}] } # needs indexing
        projection = {'ko_number': 1, 'ancestor_taxon_id': 1, 'ancestor_name': 1}
        protein = self.collection.find_one(filter=query, projection=projection,
                                            collation=self.collation)
        if protein == None:
            return 'This protein has no ancestor information to base upon'

        ancestors = protein.get('ancestor_taxon_id')
        names = protein.get('ancestor_name')
        if len(ancestors) < max_distance:
            close_relatives = ancestors
            close_names = names
        else:
            close_relatives = ancestors[-max_distance:]
            close_names = names[-max_distance:]

        ko_number = protein['ko_number']
        query = {'$and':[{'ko_number': ko_number},
                         {'ncbi_taxonomy_id': {'$in': close_relatives}}]} # needs indexing
        projection = {'abundances': 1, 'ncbi_taxonomy_id': 1, 'species_name': 1,
                    'uniprot_id': 1, '_id': 0}
        docs = self.collection.find(filter=query, projection=projection,
                                        collation=self.collation)
        if docs == None:
            return 'No proteins found within constraints'

        for i, doc in enumerate(docs):
            tax_id = doc['ncbi_taxonomy_id']
            distance = max_distance - close_relatives.index(tax_id)
            result[distance-1]['documents'].append(doc)
            result[distance-1]['ancestor_names'] = close_names

        return result

    def get_equivalent_protein(self, _id, max_distance, max_depth=float('inf')):
        '''
            Get replacement abundance value by taxonomic distance
            with the same kegg_orthology number.

            Args:
                _id (:obj:`str`): uniprot_id to query for.
                max_distance (:obj:`int`): max taxonomic distance from origin protein allowed for
                                            proteins in results.
                max_depth (:obj:`int`) max depth allowed from the common node.

            Returns:
                (:obj:`list` of :obj:`dict`): list of result proteins and their info 
                    [{'distance': 1, 'documents': [{}, {}, {} ...]}, 
                     {'distance': 2, 'documents': [{}, {}, {} ...]}, ...].
        '''

        if max_distance <= 0:
            return 'Please use get_abundance_by_id to check self abundance values'
        if max_depth == None:
            max_depth = 1000
        if max_depth <= 0:
            return 'Max_depth has to be greater than 0'

        result = []
        for i in range(max_distance):
            result.append({'distance': i + 1, 'documents': []})

        query = {'uniprot_id': {'$in': _id}}  # needs indexing
        projection = {'ko_number': 1, 'ancestor_taxon_id': 1, 'ancestor_name': 1, 'ncbi_taxonomy_id': 1}
        protein = self.collection.find_one(query, projection=projection, collation=self.collation)
        if protein is None:
            return 'This protein has no ancestor information to base upon'

        ko_number = protein['ko_number']
        ancestor_ids = protein.get('ancestor_taxon_id')
        levels = min(len(ancestor_ids), max_distance)
        checked_ids = [protein['ncbi_taxonomy_id']]

        projection = {'abundances': 1, 'ncbi_taxonomy_id': 1, 'species_name': 1,
                    'uniprot_id': 1, '_id': 0, 'ancestor_taxon_id': 1}
        for level in range(levels):
            cur_id = ancestor_ids[-(level+1)]

            if level == 0:
                common_ancestors = ancestor_ids
            else:
                common_ancestors = ancestor_ids[:-(level)]
            length = len(common_ancestors)

            query = {'$and': [{'ancestor_taxon_id': {'$all': common_ancestors} },{'ncbi_taxonomy_id': {'$nin': checked_ids} },
                              {'ancestor_taxon_id': {'$nin': checked_ids} }, {'ko_number': ko_number},
                              {'abundances': {'$exists': True} }]}

            equivalents = self.collection.find(filter=query, projection=projection)
            for equivalent in equivalents:
                depth = len(equivalent['ancestor_taxon_id']) - length
                if 0 <= depth < max_depth:
                    equivalent['depth'] = depth + 1
                    tmp = equivalent.pop('ancestor_taxon_id')
                    result[level]['documents'].append(equivalent)
            checked_ids.append(cur_id)

        return result

    def get_equivalent_protein_with_anchor(self, _id, max_distance, max_depth=float('inf')):
        '''
            Get replacement abundance value by taxonomic distance
            with the same kegg_orthology number.

            Args:
                _id (:obj:`str`): uniprot_id to query for.
                max_distance (:obj:`int`): max taxonomic distance from origin protein allowed for
                                            proteins in results.
                max_depth (:obj:`int`) max depth allowed from the common node.

            Returns:
                (:obj:`list` of :obj:`dict`): list of result proteins and their info 
                    [{'distance': 0, 'documents': [{}]}
                     {'distance': 1, 'documents': [{}, {}, {} ...]}, 
                     {'distance': 2, 'documents': [{}, {}, {} ...]}, ...].
        '''

        if max_distance <= 0:
            return 'Please use get_abundance_by_id to check self abundance values'
        if max_depth == None:
            max_depth = 1000
        if max_depth <= 0:
            return 'Max_depth has to be greater than 0'

        result = []
        for i in range(max_distance):
            result.append({'distance': i, 'documents': []})

        query = {'uniprot_id': _id}  # needs indexing
        projection = {
            'ko_number': 1,
            'ko_name': 1,
            'ancestor_taxon_id': 1,
            'ancestor_name': 1,
            'ncbi_taxonomy_id': 1,
            'abundances': 1,
            'ncbi_taxonomy_id': 1,
            'species_name': 1,
            'uniprot_id': 1,
            '_id': 0,
            'ancestor_taxon_id': 1
        }
        protein = self.collection.find_one(query, projection=projection)
        if protein is None:
            return [{'distance': -1, 'documents': []}]
        elif protein.get('ko_number') is None:
            return [{'distance': -2, 'documents': []}]
        elif protein.get('abundances') is None:
            result[0] = result[0]
        else:
            dic = {}
            dic['abundances'] = protein['abundances']
            dic['ncbi_taxonomy_id'] = protein['ncbi_taxonomy_id']
            dic['species_name'] = protein['species_name']
            dic['uniprot_id'] = _id
            dic['depth'] = 0
            dic['ko_number'] = protein['ko_number']
            dic['ko_name'] = protein['ko_name']
            result[0]['documents'].append(dic)

        ko_number = protein['ko_number']
        ancestor_ids = protein.get('ancestor_taxon_id')
        levels = min(len(ancestor_ids), max_distance)
        checked_ids = [protein['ncbi_taxonomy_id']]

        projection = {'abundances': 1, 'ncbi_taxonomy_id': 1, 'species_name': 1,
                    'uniprot_id': 1, '_id': 0, 'ancestor_taxon_id': 1, 'ko_number': 1,
                    'ko_name': 1}
        for level in range(levels):
            cur_id = ancestor_ids[-(level+1)]

            if level == 0:
                common_ancestors = ancestor_ids
            else:
                common_ancestors = ancestor_ids[:-(level)]
            length = len(common_ancestors)

            query = {'$and': [{'ancestor_taxon_id': {'$all': common_ancestors} },{'ncbi_taxonomy_id': {'$nin': checked_ids} },
                              {'ancestor_taxon_id': {'$nin': checked_ids} }, {'ko_number': ko_number.upper()},
                              {'abundances': {'$exists': True} }]}

            equivalents = self.collection.find(filter=query, projection=projection)
            for equivalent in equivalents:
                depth = len(equivalent['ancestor_taxon_id']) - length
                if 0 <= depth < max_depth:
                    equivalent['depth'] = depth + 1
                    tmp = equivalent.pop('ancestor_taxon_id')
                    result[level]['documents'].append(equivalent)
            checked_ids.append(cur_id)

        return result

    def get_uniprot_by_ko(self, ko):
        '''
            Find all proteins with the same kegg orthology id.

            Args:
                ko (:obj:`str`): kegg orthology ID.

            Return:
                (:obj:`list` of :obj:`str`): list of uniprot_id.
        '''
        ko = ko.upper()
        result = []
        query = {'ko_number': ko}
        projection = {'uniprot_id': 1, '_id': 0}
        docs = self.collection.find(filter=query, projection=projection)
        count = self.collection.count_documents(query)

        if count == 0:
            return 'No information available for this KO.'

        for doc in docs:
            result.append(doc['uniprot_id'])
        return result


    '''
        The methods below are "super" methods that try to predict some 
        commonly used functionalities for modelers
    '''


    def get_abundance_with_same_ko(self, _id):
        '''Find abundance information for protein with the same
            KO number.

            Args:
                _id (:obj:`str`): uniprot ID.

            Returns:
                (:obj:`list` of :obj:`dict`): information
                [{'uniprot_id': , 'abundances': }, {},...,{}].
        '''

        query = {'uniprot_id': _id}
        projection = {'_id': 0, 'ko_number': 1, 'ncbi_taxonomy_id': 1, 'uniprot_id': 1}
        doc = self.collection.find_one(filter=query, projection=projection, collation=self.collation)
        if doc is None:
            return 'No such protein in the database.'
        else:
            ko_number = doc.get('ko_number')

        if ko_number is None:
            return 'No kegg information available for this protein.'

        query = {'$and': [{'ko_number': ko_number}, {'abundances': {'$exists': True} }]}
        projection = {'ancestor_name': 0, 'ancestor_taxon_id': 0, '_id': 0}
        result = []
        docs = self.collection.find(filter=query, projection=projection)
        for doc in docs:
            result.append(doc)
        return result

    def get_abundance_by_ko(self, ko):
        ''' Get abundance information of proteins with
            the same KO.

            Args:
                ko (:obj:`str`): KO number.

            Returns:
                (:obj:`list` of :obj:`dict`): information
                [{'uniprot_id': , 'abundances': }, {},...,{}].             
        '''
        query = {'$and': [{'ko_number': ko.upper()}, {'abundances': {'$exists': True} }]}
        projection = {'abundances': 1, 'uniprot_id': 1, '_id': 0}
        result = []
        docs = self.collection.find(filter=query, projection=projection)
        if docs == None:
            return {'abundances': [], 'uniprot_id': 'No proteins match input information.'}
        for doc in docs:
            result.append(doc)
        return result
    
    def get_kegg_orthology(self, uniprot_id):
        """Get protein's kegg orthology number given uniprot id.
        
        Args:
            uniprot_id (:obj:`str`): protein's uniprot id.

        Returns:
            (:obj:`tuple`): tuple containing:
                (:obj:`str`): kegg orthology id;
                (:obj:`list` of :obj:`str`): list of kegg orthology descriptions.
        """
        query = {'uniprot_id': uniprot_id}
        projection = {'_id': 0, 'ko_number': 1, 'ko_name': 1}
        doc = self.collection.find_one(filter=query, projection=projection)
        if doc is not None:
            return doc.get('ko_number'), doc.get('ko_name', [])
        else:
            return None, []

    def get_equivalent_kegg_with_anchor_obsolete(self, ko, anchor, max_distance, max_depth=float('inf')):
        '''
            Get replacement abundance value by taxonomic distance
            with the same kegg_orthology number.

            Args:
                ko (:obj:`str`): kegg orthology id to query for.
                anchor (:obj:`str`): anchor species' name.
                max_distance (:obj:`int`): max taxonomic distance from origin protein allowed for
                                            proteins in results.
                max_depth (:obj:`int`) max depth allowed from the common node.

            Returns:
                (:obj:`list` of :obj:`dict`): list of result proteins and their info 
                    [{'distance': 0, 'documents': [{}]}
                     {'distance': 1, 'documents': [{}, {}, {} ...]}, 
                     {'distance': 2, 'documents': [{}, {}, {} ...]}, ...].
        '''

        if max_distance <= 0:
            return 'Please use get_abundance_by_id to check self abundance values'
        if max_depth == None:
            max_depth = 1000
        if max_depth <= 0:
            return 'Max_depth has to be greater than 0'

        result = []
        for i in range(max_distance):
            result.append({'distance': i, 'documents': []})

        ko_number = ko
        ancestor_ids, _ = self.taxon_manager.get_anc_by_name([anchor])
        ancestor_ids = ancestor_ids[0]
        ncbi_id = self.taxon_manager.get_ids_by_name(anchor)
        constraint_0 = {'ko_number': ko_number}
        constraint_1 = {'ncbi_taxonomy_id': {'$in': ncbi_id}}
        query = {'$and': [constraint_0, constraint_1]}
        projection = {
            'ko_number': 1,
            'ko_name': 1,
            'ancestor_name': 1,
            'ncbi_taxonomy_id': 1,
            'abundances': 1,
            'species_name': 1,
            'uniprot_id': 1,
            '_id': 0,
            'ancestor_taxon_id': 1,
            'protein_name': 1,
            'gene_name': 1
        }
        docs = self.collection.find(filter=query, projection=projection, collation=self.collation)
        if docs is not None:
            for doc in docs:
                result[0]['documents'].append(doc)

        levels = min(len(ancestor_ids), max_distance)
        checked_ids = ncbi_id

        projection = {'abundances': 1, 'ncbi_taxonomy_id': 1, 'species_name': 1,
                    'uniprot_id': 1, '_id': 0, 'ancestor_taxon_id': 1, 'ko_number': 1,
                    'ko_name': 1, 'protein_name': 1, 'gene_name': 1}
        for level in range(levels):
            cur_id = ancestor_ids[-(level+1)]

            if level == 0:
                common_ancestors = ancestor_ids
            else:
                common_ancestors = ancestor_ids[:-(level)]
            length = len(common_ancestors)

            query = {'$and': [{'ancestor_taxon_id': {'$all': common_ancestors} },{'ncbi_taxonomy_id': {'$nin': checked_ids} },
                              {'ancestor_taxon_id': {'$nin': checked_ids} }, {'ko_number': ko_number},
                              {'abundances': {'$exists': True} }]}

            equivalents = self.collection.find(filter=query, projection=projection)
            for equivalent in equivalents:
                depth = len(equivalent['ancestor_taxon_id']) - length
                if 0 <= depth < max_depth:
                    equivalent['depth'] = depth + 1
                    tmp = equivalent.pop('ancestor_taxon_id')
                    result[level]['documents'].append(equivalent)
            checked_ids.append(cur_id)

        return result

    def get_unique_protein(self):
        """Get number of unique proteins in collection

        Return:
            (:obj:`int`): number of unique proteins.
        """
        return len(self.collection.distinct('uniprot_id', collation=self.collation))
    
    def get_unique_organism(self):
        """Get number of unique organisms in collection.

        Return:
            (:obj:`int`): number of unique organisms.
        """
        return len(self.collection.distinct('ncbi_taxonomy_id'))

    def get_all_kegg(self, ko, anchor, max_distance):
        '''Get replacement abundance value by taxonomic distance
            with the same kegg_orthology number.

        Args:
            ko (:obj:`str`): kegg orthology id to query for.
            anchor (:obj:`str`): anchor species' name.
            max_distance (:obj:`int`): max taxonomic distance from origin protein allowed for
                                        proteins in results.
            max_depth (:obj:`int`) max depth allowed from the common node.

        Returns:
            (:obj:`list` of :obj:`dict`): list of result proteins and their info 
            [
            {'distance': 1, 'documents': [{}, {}, {} ...]}, 
            {'distance': 2, 'documents': [{}, {}, {} ...]}, ...].
        '''
        if max_distance <= 0:
            return 'Please use get_abundance_by_id to check self abundance values'

        result = []
        for i in range(max_distance):
            result.append({'distance': i + 1, 'documents': []})

        projection = {
            'ko_number': 1,
            'ko_name': 1,
            'ancestor_name': 1,
            'ncbi_taxonomy_id': 1,
            'abundances': 1,
            'species_name': 1,
            'uniprot_id': 1,
            '_id': 0,
            'ancestor_taxon_id': 1,
            'protein_name': 1,
            'gene_name': 1,
            'modifications': 1
        }
        con_0 = {'ko_number': ko}
        con_1 = {'abundances': {'$exists': True}}
        query = {'$and': [con_0, con_1]}
        docs = self.collection.find(filter=query, projection=projection)
        queried = deque()
        names = {}
        for doc in docs:
            doc = json.loads(json.dumps(doc, ignore_nan=True))
            species = doc.get('species_name')
            if species is None and species not in queried:
                taxon_id = doc['ncbi_taxonomy_id']
                species = self.db_obj['taxon_tree'].find_one({"tax_id": taxon_id})['tax_name']
                queried.append(taxon_id)
                names[taxon_id] = species
            elif species is None and species in queried:
                species = names[doc['ncbi_taxonomy_id']]
            obj = self.taxon_manager.get_canon_common_ancestor(anchor, species, org_format='tax_name')
            distance = obj[anchor]            
            if distance != -1 and distance <= max_distance:
                species_canon_ancestor = obj[species+'_canon_ancestors']
                doc['canon_ancestors'] = species_canon_ancestor
                result[distance-1]['documents'].append(doc)
        return result

    def get_all_ortho(self, ko, anchor, max_distance):
        '''Get replacement abundance value by taxonomic distance
            with the same OrthoDB group number.

        Args:
            ko (:obj:`str`): OrthoDB group id to query for.
            anchor (:obj:`str`): anchor species' name.
            max_distance (:obj:`int`): max taxonomic distance from origin protein allowed for
                                        proteins in results.
            max_depth (:obj:`int`) max depth allowed from the common node.

        Returns:
            (:obj:`list` of :obj:`dict`): list of result proteins and their info 
            [
            {'distance': 1, 'documents': [{}, {}, {} ...]}, 
            {'distance': 2, 'documents': [{}, {}, {} ...]}, ...].
        '''
        if max_distance <= 0:
            return 'Please use get_abundance_by_id to check self abundance values'

        result = []
        for i in range(max_distance):
            result.append({'distance': i + 1, 'documents': []})

        projection = {
            'orthodb_id': 1,
            'orthodb_name': 1,
            'ncbi_taxonomy_id': 1,
            'abundances': 1,
            'species_name': 1,
            'uniprot_id': 1,
            '_id': 0,
            'protein_name': 1,
            'gene_name': 1,
            'modifications': 1,
            "canon_anc_ids": 1,
            "canon_anc_names": 1
        }
        con_0 = {'orthodb_id': ko}
        con_1 = {'abu_exist': True}
        query = {'$and': [con_0, con_1]}
        docs = self.collection.find(filter=query, projection=projection,
                                    hint=[("abu_exist", ASCENDING), ("orthodb_id", ASCENDING)],
                                    batch_size=100)
        queried = deque()
        distances = {}
        names = {}
        species_anc = {}
        canon_anc_anchor = self.taxon_col.find_one({"tax_name": anchor})['canon_anc_names']
        for doc in docs:
            doc = json.loads(json.dumps(doc, ignore_nan=True))
            species = doc.get('species_name')
            taxon_id = doc['ncbi_taxonomy_id']
            if species is None and taxon_id not in queried: # few documents don't have species_name field
                tmp = self.taxon_col.find_one({"tax_id": taxon_id})
                species = tmp['tax_name']
                canon_anc_species = tmp["canon_anc_names"]
                queried.append(taxon_id)
                names[taxon_id] = species
                species_anc[taxon_id] = canon_anc_species
                obj = self._get_common_canon_anc(anchor, species, canon_anc_anchor, doc["canon_anc_names"])
                distances[taxon_id] = obj
            elif species is not None and taxon_id not in queried:
                canon_anc_species = doc["canon_anc_names"]
                queried.append(taxon_id)
                names[taxon_id] = species
                species_anc[taxon_id] = canon_anc_species
                obj = self._get_common_canon_anc(anchor, species, canon_anc_anchor, doc["canon_anc_names"])
                distances[taxon_id] = obj                
            else:
                species = names[taxon_id]
                canon_anc_species = species_anc[taxon_id]
                obj = distances[taxon_id]            
            distance = obj[anchor]            
            if distance != -1 and distance <= max_distance:
                species_canon_ancestor = obj[species+'_canon_ancestors']
                doc['canon_ancestors'] = species_canon_ancestor
                result[distance-1]['documents'].append(doc)
        return result

    def _get_common_canon_anc(self, org1, org2, canon_anc_1, canon_anc_2):
        """Get canon common ancestors between species.

        Args:
            org1(:obj:`str`): Name of species 1.
            org2(:obj:`str`): Name of species 2.
            canon_anc_1(:obj:`list` of `str`): List of canon ancestor names of species 1.
            canon_anc_2(:obj:`list` of `str`): List of canon ancestor names of species 2.

        Return:
            (:obj:`Obj`): {str(org1): distance1, str(org2): distance2, str(org1)+'_canon_ancestors':canon_anc_1,
                           str(org2)+'_canon_ancestors':canon_anc_2}
        """
        if canon_anc_1 == canon_anc_2:
            return {str(org1): 0, str(org1)+'_canon_ancestors':canon_anc_1,
                    str(org2): 0, str(org2)+'_canon_ancestors':canon_anc_1}

        if canon_anc_1[-1] == org2:
            distance1 = 1
            distance2 = 0
        elif canon_anc_2[-1] == org1:
            distance1 = 0
            distance2 = 1
        else:
            distance1 = -1
            distance2 = -1            
        ancestor = self.file_manager.get_common(canon_anc_1, canon_anc_2)
        if ancestor == '':                
            return {str(org1): -1, str(org2): -1, 'reason': 'No common ancestor.'}

        idx_org1 = canon_anc_1.index(ancestor)
        idx_org2 = canon_anc_2.index(ancestor)

        if distance1 == -1:
            distance1 = len(canon_anc_1) - (idx_org1) 
        if distance2 == -1:
            distance2 = len(canon_anc_2) - (idx_org2)

        return {str(org1): distance1, str(org2): distance2, str(org1)+'_canon_ancestors':canon_anc_1,
        str(org2)+'_canon_ancestors':canon_anc_2}

    def get_info_by_orthodb(self, orthodb):
        '''
            Find all proteins with the same kegg orthology id.

            Args:
                orthodb(:obj:`str`): kegg orthology ID.

            Returns:
                (:obj:`list` of :obj:`dict`): list of dictionary containing 
                protein's uniprot_id and kegg information
                [{'orthodb_id': ... 'orthodb_name': ... 'uniprot_ids': []},
                 {'orthodb_id': ... 'orthodb_name': ... 'uniprot_ids': []}].
        '''
        ko = orthodb.lower()
        result = [{'orthodb_id': ko, 'uniprot_ids': []}]
        query = {'orthodb_id': ko}
        projection = {'uniprot_id': 1, '_id': 0, 'orthodb_name': 1, 'orthodb_id': 1}
        docs = self.collection.find(filter=query, projection=projection)

        for doc in docs:
            result[0]['orthodb_name'] = doc.get('orthodb_name', ['no name'])
            result[0]['uniprot_ids'].append(doc.get('uniprot_id'))
        return result