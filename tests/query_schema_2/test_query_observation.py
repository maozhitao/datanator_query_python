from datanator_query_python.query_schema_2 import query_observation
import unittest


class TestQOb(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.src = query_observation.QueryObs()

    @classmethod
    def tearDownClass(cls):
        cls.src.client.close()

    def test_get_entity_datatype(self):
        identfier = {"namespace": "gene_symbol", "value": "BAG1"}
        results = self.src.get_entity_datatype(identfier)
        self.assertEqual(results[0]["entity"]["name"], 'BCL2-associated athanogene.')
        identfier = {"namespace": "gene_symbol", "value": "something"}
        results = self.src.get_entity_datatype(identfier)
        self.assertEqual(results, [])
        identfier = {"namespace": "gene_name", "value": "EMC3"}
        results = self.src.get_entity_datatype(identfier, datatype="localization")
        self.assertEqual(results[0]["entity"]["name"], 'ER membrane protein complex subunit 3')
        identfier = {"namespace": "gene_id", "value": "100003563"}
        results = self.src.get_entity_datatype(identfier, entity="RNA", datatype="localization")
        self.assertEqual(results[0]["genotype"]["taxon"]["name"], 'Danio rerio')