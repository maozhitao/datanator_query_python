from datanator_query_python.config import query_schema_2_manager


class QueryObs(query_schema_2_manager.QM):
    def __init__(self,
                 db="datanator-demo"):
        super().__init__()
        self.db = db

    def get_protein_halflives(self, 
                              identifier,
                              collection="observation",
                              limit=10,
                              skip=0):
        """Get protein halflives.

        Args:
            identifier(:obj:`Obj`): identifier used for the protein.
            collection(:obj:`str`, optional): name of collection in which values reside.
            limit(:obj:`int`, optional): number of results to return.
            skip(:obj:`int`, optional): number of documents to skip.

        Return:
            (:obj:`list`): pymongo iterables.
        """
        results = []
        col = self.client[self.db][collection]
        con_0 = {"entity.type": "protein"}
        con_1 = {"values.type": "half-life"}
        query = {"$and": [{"identifier": identifier}, con_0, con_1]}
        docs = col.find(filter=query, limit=limit, skip=skip,
                        collation=self.collation)
        for doc in docs:
            results.append(doc)
        return results