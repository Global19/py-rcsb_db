##
# File:    SchemaDefBuildTests.py
# Author:  J. Westbrook
# Date:    9-Jun-2018
# Version: 0.001
#
# Update:
#
##
"""
Tests for utilities employed to construct local and json schema defintions from
dictionary metadata and user preference data.

"""

__docformat__ = "restructuredtext en"
__author__ = "John Westbrook"
__email__ = "jwest@rcsb.rutgers.edu"
__license__ = "Apache 2.0"


import logging
import os
import sys
import time
import unittest

HERE = os.path.abspath(os.path.dirname(__file__))
TOPDIR = os.path.dirname(os.path.dirname(HERE))

try:
    from rcsb_db import __version__
except Exception as e:
    sys.path.insert(0, TOPDIR)
    from rcsb_db import __version__

from rcsb_db.define.SchemaDefBuild import SchemaDefBuild
#
from rcsb_db.helpers.DictInfoHelper import DictInfoHelper
from rcsb_db.helpers.SchemaDefHelper import SchemaDefHelper
from rcsb_db.helpers.SchemaDocumentHelper import SchemaDocumentHelper
from rcsb_db.io.IoUtil import IoUtil

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s]-%(module)s.%(funcName)s: %(message)s')
logger = logging.getLogger()
logger.setLevel(logging.INFO)


class SchemaDefBuildTests(unittest.TestCase):

    def setUp(self):
        self.__verbose = True
        self.__pathPdbxDictionaryFile = os.path.join(TOPDIR, 'rcsb_db', 'data', 'dictionaries', 'mmcif_pdbx_v5_next.dic')
        self.__pathRcsbDictionaryFile = os.path.join(TOPDIR, 'rcsb_db', 'data', 'dictionaries', 'rcsb_mmcif_ext_v1.dic')
        #
        self.__startTime = time.time()
        logger.debug("Running tests on version %s" % __version__)
        logger.debug("Starting %s at %s" % (self.id(),
                                            time.strftime("%Y %m %d %H:%M:%S", time.localtime())))

    def tearDown(self):
        endTime = time.time()
        logger.debug("Completed %s at %s (%.4f seconds)" % (self.id(),
                                                            time.strftime("%Y %m %d %H:%M:%S", time.localtime()),
                                                            endTime - self.__startTime))

    def testBuild(self):
        schemaNames = ['pdbx', 'pdbx_core', 'chem_comp', 'bird', 'bird_family', 'bird_chem_comp']
        applicationNames = ['ANY', 'SQL']
        for schemaName in schemaNames:
            for applicationName in applicationNames:
                self.__testBuild(schemaName, applicationName)

    def testBuildJson(self):
        schemaNames = ['pdbx', 'pdbx_core', 'chem_comp', 'bird', 'bird_family']
        collectionNames = {'pdbx': ['pdbx_v5_0_2', 'pdbx_ext_v5_0_2'],
                           'pdbx_core': ['pdbx_core_entity_v5_0_2', 'pdbx_core_entry_v5_0_2'],
                           'bird': ['bird_v5_0_2'],
                           'bird_family': ['family_v5_0_2'],
                           'chem_comp': ['chem_comp_v5_0_2'],
                           'bird_chem_comp': ['bird_chem_comp_v5_0_2']}
        #
        for schemaName in schemaNames:
            for collectionName in collectionNames[schemaName]:
                self.__testBuildJson(schemaName, collectionName)

    def __testBuild(self, schemaName, applicationName):
        try:
            contentType = schemaName[:4] if schemaName.startswith('pdbx') else schemaName
            instDataTypeFilePath = os.path.join(TOPDIR, 'rcsb_db', 'data', 'data_type_info', 'scan-%s-type-map.json' % contentType)
            appDataTypeFilePath = os.path.join(TOPDIR, 'rcsb_db', 'data', 'data_type_info', 'app_data_type_mapping.cif')
            #
            pathSchemaDefJson = os.path.join(HERE, 'test-output', 'schema_def-%s-%s.json' % (schemaName, applicationName))
            #
            dictInfoHelper = DictInfoHelper()
            defHelper = SchemaDefHelper()
            docHelper = SchemaDocumentHelper()
            #
            smb = SchemaDefBuild(schemaName,
                                 dictLocators=[self.__pathPdbxDictionaryFile, self.__pathRcsbDictionaryFile],
                                 instDataTypeFilePath=instDataTypeFilePath,
                                 appDataTypeFilePath=appDataTypeFilePath,
                                 dictHelper=dictInfoHelper,
                                 schemaDefHelper=defHelper,
                                 documentDefHelper=docHelper,
                                 applicationName=applicationName)
            cD = smb.build()
            #
            logger.debug("Schema dictionary category length %d" % len(cD['SCHEMA_DICT']))
            self.assertGreaterEqual(len(cD['SCHEMA_DICT']), 5)
            #
            ioU = IoUtil()
            ioU.serialize(pathSchemaDefJson, cD, format='json', indent=3)

        except Exception as e:
            logger.exception("Failing with %s" % str(e))
            self.fail()

    def __testBuildJson(self, schemaName, collectionName):
        try:
            contentType = schemaName[:4] if schemaName.startswith('pdbx') else schemaName
            instDataTypeFilePath = os.path.join(TOPDIR, 'rcsb_db', 'data', 'data_type_info', 'scan-%s-type-map.json' % contentType)
            appDataTypeFilePath = os.path.join(TOPDIR, 'rcsb_db', 'data', 'data_type_info', 'app_data_type_mapping.cif')
            #
            # pathSchemaDefJson = os.path.join(HERE, 'test-output', 'json-schema-%s-%s.json' % (schemaName, collectionName))
            #
            pathSchemaDefJson1 = os.path.join(HERE, 'test-output', 'json-schema-%s.json' % (collectionName))
            pathSchemaDefJson2 = os.path.join(TOPDIR, 'rcsb_db', 'data', 'json-schema', 'json-schema-%s.json' % (collectionName))
            #
            dictInfoHelper = DictInfoHelper()
            defHelper = SchemaDefHelper()
            docHelper = SchemaDocumentHelper()
            #
            smb = SchemaDefBuild(schemaName,
                                 dictLocators=[self.__pathPdbxDictionaryFile, self.__pathRcsbDictionaryFile],
                                 instDataTypeFilePath=instDataTypeFilePath,
                                 appDataTypeFilePath=appDataTypeFilePath,
                                 dictHelper=dictInfoHelper,
                                 schemaDefHelper=defHelper,
                                 documentDefHelper=docHelper,
                                 applicationName='json')
            cD = smb.build(collectionName, schemaType='json')
            #
            logger.debug("Schema dictionary category length %d" % len(cD['properties']))
            self.assertGreaterEqual(len(cD['properties']), 5)
            #
            ioU = IoUtil()
            ioU.serialize(pathSchemaDefJson1, cD, format='json', indent=3)
            ioU.serialize(pathSchemaDefJson2, cD, format='json', indent=3)

        except Exception as e:
            logger.exception("Failing with %s" % str(e))
            self.fail()


def schemaBuildSuite():
    suiteSelect = unittest.TestSuite()
    suiteSelect.addTest(SchemaDefBuildTests("testBuild"))
    return suiteSelect


def schemaBuildJsonSuite():
    suiteSelect = unittest.TestSuite()
    suiteSelect.addTest(SchemaDefBuildTests("testBuildJson"))
    return suiteSelect


if __name__ == '__main__':
    #
    if True:
        mySuite = schemaBuildSuite()
        unittest.TextTestRunner(verbosity=2).run(mySuite)
    if True:
        mySuite = schemaBuildJsonSuite()
        unittest.TextTestRunner(verbosity=2).run(mySuite)
